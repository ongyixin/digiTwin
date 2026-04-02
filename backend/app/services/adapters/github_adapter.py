"""GitHub repo adapter — ingests repositories, PRs, issues, and ADRs
into the knowledge graph using the GitHub API and Tree-sitter code parsing.
"""

import hashlib
import json
from typing import Callable, Optional

from neo4j import AsyncDriver

from app.llm.base import GenerateConfig, LLMProvider
from app.models.artifact import ArtifactIngestRequest, ArtifactIngestResult
from app.services.adapters.base import BaseAdapter
from app.services.graph_service import GraphService, _new_id


class GitHubRepoAdapter(BaseAdapter):
    """Ingestion adapter for GitHub repositories.

    Pipeline:
    1. Auth (GitHub App or PAT)
    2. Enumerate repository files
    3. Fetch file contents
    4. Parse code with Tree-sitter (symbols, modules)
    5. LLM-based architectural extraction
    6. Embedding + graph upsert
    7. Provenance linking
    """

    @property
    def pipeline_stages(self) -> list[str]:
        return [
            "auth",
            "enumerate",
            "fetch_files",
            "parse_code",
            "extract_symbols",
            "extract_architecture",
            "embedding",
            "graph_upsert",
            "provenance",
        ]

    async def ingest(
        self,
        request: ArtifactIngestRequest,
        raw_content: Optional[bytes | str],
        driver: AsyncDriver,
        llm: LLMProvider,
        job_emitter: Optional[Callable] = None,
    ) -> ArtifactIngestResult:
        from app.services.github.github_fetcher import GitHubFetcher
        from app.services.github.code_parser import CodeParser

        graph = GraphService(driver)
        repo_url = request.github_repo_url or request.source_url or request.metadata.get("repo_url", "")
        if not repo_url:
            raise ValueError("github_repo_url is required for github_repo artifacts")

        # Parse owner/repo from URL
        owner, repo_name = _parse_repo_url(repo_url)
        title = f"{owner}/{repo_name}"
        artifact_id = _new_id("ART")
        artifact_version_id = _new_id("AV")

        # Auth
        await self._emit(job_emitter, "stage_started", stage="auth", detail=f"Authenticating for {title}")
        fetcher = GitHubFetcher(
            installation_id=request.github_installation_id or request.metadata.get("installation_id"),
        )
        await fetcher.authenticate()
        await self._emit(job_emitter, "stage_completed", stage="auth", entities_found=1)

        # Enumerate
        await self._emit(job_emitter, "stage_started", stage="enumerate",
                         detail=f"Enumerating {title}@{request.github_branch}")
        file_tree = await fetcher.enumerate_files(owner, repo_name, request.github_branch)
        await self._emit(job_emitter, "stage_completed", stage="enumerate", entities_found=len(file_tree))

        # Register artifact
        await graph.upsert_artifact(
            artifact_id=artifact_id,
            artifact_type="github_repo",
            source_type="github",
            title=title,
            workspace_id=request.workspace_id,
            sensitivity=request.sensitivity,
            mime_type="application/x-git",
            metadata={**request.metadata, "repo_url": repo_url, "branch": request.github_branch, "owner": owner, "repo": repo_name},
        )
        # Use latest commit SHA as version boundary
        latest_sha = await fetcher.get_latest_sha(owner, repo_name, request.github_branch)
        await graph.upsert_artifact_version(
            version_id=artifact_version_id,
            artifact_id=artifact_id,
            content_hash=latest_sha[:16],
            model_version="gemini-2.5-flash",
        )

        # Fetch file contents
        await self._emit(job_emitter, "stage_started", stage="fetch_files",
                         detail=f"Fetching {len(file_tree)} files")
        files = await fetcher.fetch_files(owner, repo_name, file_tree, max_files=200)
        await self._emit(job_emitter, "stage_completed", stage="fetch_files", entities_found=len(files))

        # Parse code with Tree-sitter
        await self._emit(job_emitter, "stage_started", stage="parse_code",
                         detail=f"Parsing {len(files)} files")
        parser = CodeParser()
        all_symbols: list[dict] = []
        file_nodes: list[dict] = []
        for file_path, content in files.items():
            symbols = parser.extract_symbols(file_path, content)
            all_symbols.extend(symbols)
            file_nodes.append({"path": file_path, "content": content[:500], "symbol_count": len(symbols)})
        await self._emit(job_emitter, "stage_completed", stage="parse_code", entities_found=len(all_symbols))

        # Repository node
        repo_node_id = await graph.upsert_repository(
            owner=owner,
            repo_name=repo_name,
            repo_url=repo_url,
            branch=request.github_branch,
            workspace_id=request.workspace_id,
            artifact_version_id=artifact_version_id,
        )

        # Upsert file and symbol nodes
        await self._emit(job_emitter, "stage_started", stage="extract_symbols",
                         detail=f"Upserting {len(all_symbols)} symbols")
        symbol_count = 0
        for sym in all_symbols:
            embedding = await llm.embed(f"{sym.get('kind', '')} {sym.get('name', '')} {sym.get('docstring', '')}")
            await graph.upsert_symbol(
                name=sym.get("name", ""),
                kind=sym.get("kind", "function"),
                file_path=sym.get("file_path", ""),
                line_start=sym.get("line_start", 0),
                line_end=sym.get("line_end", 0),
                docstring=sym.get("docstring", ""),
                repo_node_id=repo_node_id,
                embedding=embedding,
                workspace_id=request.workspace_id,
                artifact_version_id=artifact_version_id,
            )
            symbol_count += 1
        await self._emit(job_emitter, "stage_completed", stage="extract_symbols", entities_found=symbol_count)

        # Architecture / ADR extraction via LLM on README / docs
        await self._emit(job_emitter, "stage_started", stage="extract_architecture",
                         detail="Extracting architectural decisions from docs")
        readme_content = files.get("README.md", "") or files.get("readme.md", "") or ""
        arch_entities: dict = {}
        if readme_content:
            arch_entities = await _extract_repo_entities(llm, readme_content, repo_url, title)
        await self._emit(job_emitter, "stage_completed", stage="extract_architecture",
                         entities_found=sum(len(v) for v in arch_entities.values()))

        # Embedding for file nodes
        await self._emit(job_emitter, "stage_started", stage="embedding")
        chunk_count = 0
        for f_node in file_nodes[:100]:  # limit to first 100 files
            embedding = await llm.embed(f"{f_node['path']} {f_node['content']}")
            chunk_id = _new_id("CHK")
            await graph.upsert_chunk(
                chunk_id=chunk_id,
                artifact_version_id=artifact_version_id,
                sequence=chunk_count,
                text=f"{f_node['path']}: {f_node['content']}",
                embedding=embedding,
            )
            chunk_count += 1
        await self._emit(job_emitter, "stage_completed", stage="embedding", entities_found=chunk_count)

        await self._emit(job_emitter, "stage_started", stage="graph_upsert")
        await self._emit(job_emitter, "stage_completed", stage="graph_upsert",
                         entities_found=symbol_count + chunk_count)

        await self._emit(job_emitter, "stage_started", stage="provenance")
        await self._emit(job_emitter, "stage_completed", stage="provenance", entities_found=chunk_count)

        return ArtifactIngestResult(
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            artifact_type="github_repo",
            entities_created={
                "files": len(file_nodes),
                "symbols": symbol_count,
                "chunks": chunk_count,
                **{k: len(v) for k, v in arch_entities.items()},
            },
            chunk_count=chunk_count,
            section_count=len(file_nodes),
        )


def _parse_repo_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL or owner/repo string."""
    url = url.rstrip("/")
    if "github.com" in url:
        parts = url.split("github.com/")[-1].split("/")
        return parts[0], parts[1].replace(".git", "")
    if "/" in url:
        parts = url.split("/")
        return parts[0], parts[1].replace(".git", "")
    raise ValueError(f"Cannot parse repo URL: {url}")


async def _extract_repo_entities(
    llm: LLMProvider,
    readme: str,
    repo_url: str,
    title: str,
) -> dict:
    """Extract architectural decisions and dependencies from README."""
    import os

    prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/extract_repo.txt")
    try:
        with open(prompt_path) as f:
            template = f.read()
    except FileNotFoundError:
        return {}

    prompt = (
        template
        .replace("{content}", readme[:8000])
        .replace("{repo_url}", repo_url)
        .replace("{title}", title)
    )
    raw = await llm.generate(prompt, GenerateConfig(temperature=0.1, response_mime_type="application/json"))
    try:
        from app.services.ingestion_service import _clean_json
        return json.loads(_clean_json(raw or "{}"))
    except Exception:
        return {}
