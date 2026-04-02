"""GitHub repo adapter — ingests repositories, PRs, issues, and ADRs
into the knowledge graph using the GitHub API and Tree-sitter code parsing.
"""

import hashlib
import json
import os
from typing import Callable, Optional

from neo4j import AsyncDriver

from app.llm.base import GenerateConfig, LLMProvider
from app.models.artifact import ArtifactIngestRequest, ArtifactIngestResult
from app.services.adapters.base import BaseAdapter
from app.services.graph_service import GraphService, _new_id

# Doc files beyond README that often contain architectural decisions
_ARCHITECTURE_FILES = {
    "ARCHITECTURE.md", "architecture.md",
    "CONTRIBUTING.md", "contributing.md",
    "DESIGN.md", "design.md",
    "CHANGELOG.md", "changelog.md",
    "docs/architecture.md", "docs/ARCHITECTURE.md",
    "docs/decisions.md", "docs/adr.md",
    "ADR.md", "adr.md",
}

# Conventional commit prefixes that signal architectural decisions
_DECISION_COMMIT_PREFIXES = (
    "feat!", "fix!", "refactor!", "perf!", "chore!",
    "BREAKING CHANGE", "breaking change",
    "migrate", "switch to", "replace ", "adopt ",
    "introduce ", "deprecate", "remove ", "drop ",
    "rewrite", "redesign", "restructure",
)


class GitHubRepoAdapter(BaseAdapter):
    """Ingestion adapter for GitHub repositories.

    Pipeline:
    1. Auth (GitHub App or PAT)
    2. Enumerate repository files
    3. Fetch file contents
    4. Parse code with Tree-sitter (symbols, modules)
    5. LLM-based architectural extraction from docs
    6. LLM-based decision extraction from commit history
    7. Embedding + graph upsert (all entities written to Neo4j)
    8. Provenance linking
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
            "extract_commits",
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

        owner, repo_name = _parse_repo_url(repo_url)
        title = f"{owner}/{repo_name}"
        artifact_id = _new_id("ART")
        artifact_version_id = _new_id("AV")
        workspace = request.workspace_id
        sensitivity = request.sensitivity

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
            workspace_id=workspace,
            sensitivity=sensitivity,
            mime_type="application/x-git",
            metadata={**request.metadata, "repo_url": repo_url, "branch": request.github_branch, "owner": owner, "repo": repo_name},
        )
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
            workspace_id=workspace,
            artifact_version_id=artifact_version_id,
        )

        # Upsert symbol nodes
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
                workspace_id=workspace,
                artifact_version_id=artifact_version_id,
            )
            symbol_count += 1
        await self._emit(job_emitter, "stage_completed", stage="extract_symbols", entities_found=symbol_count)

        # Architecture / ADR extraction from README + other doc files
        await self._emit(job_emitter, "stage_started", stage="extract_architecture",
                         detail="Extracting architectural decisions from docs")
        doc_content = _collect_doc_content(files)
        arch_entities: dict = {}
        if doc_content:
            arch_entities = await _extract_repo_entities(llm, doc_content, repo_url, title)
        arch_counts = await _upsert_repo_entities(
            graph, llm, arch_entities, repo_url, workspace, sensitivity, artifact_version_id
        )
        await self._emit(job_emitter, "stage_completed", stage="extract_architecture",
                         entities_found=sum(arch_counts.values()))

        # Commit-history decision extraction
        await self._emit(job_emitter, "stage_started", stage="extract_commits",
                         detail="Scanning commit history for architectural decisions")
        commit_counts: dict[str, int] = {}
        try:
            commits = await fetcher.fetch_commits(owner, repo_name, request.github_branch, limit=100)
            significant = _filter_significant_commits(commits)
            if significant:
                commit_entities = await _extract_commit_decisions(llm, significant, repo_url, title)
                commit_counts = await _upsert_repo_entities(
                    graph, llm, commit_entities, repo_url, workspace, sensitivity, artifact_version_id
                )
        except Exception as exc:
            print(f"Commit extraction failed (non-fatal): {exc}")
        await self._emit(job_emitter, "stage_completed", stage="extract_commits",
                         entities_found=sum(commit_counts.values()))

        # Embedding for file nodes
        await self._emit(job_emitter, "stage_started", stage="embedding")
        chunk_count = 0
        for f_node in file_nodes[:100]:
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

        total_knowledge_entities = sum(arch_counts.values()) + sum(commit_counts.values())
        await self._emit(job_emitter, "stage_started", stage="graph_upsert")
        await self._emit(job_emitter, "stage_completed", stage="graph_upsert",
                         entities_found=symbol_count + chunk_count + total_knowledge_entities)

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
                **{f"arch_{k}": v for k, v in arch_counts.items() if v},
                **{f"commit_{k}": v for k, v in commit_counts.items() if v},
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


def _collect_doc_content(files: dict[str, str]) -> str:
    """Combine README + known architecture docs into a single extraction input."""
    parts: list[str] = []
    # README first
    for key in ("README.md", "readme.md", "README.rst", "README.txt"):
        if key in files:
            parts.append(files[key])
            break
    # Additional architecture/decision docs
    for path, content in files.items():
        basename = path.split("/")[-1]
        if path in _ARCHITECTURE_FILES or basename in _ARCHITECTURE_FILES:
            if content not in parts:
                parts.append(f"\n\n---\n# {path}\n\n{content}")
    return "\n".join(parts)


def _filter_significant_commits(commits: list[dict]) -> list[dict]:
    """Return commits likely to represent architectural decisions."""
    significant = []
    for c in commits:
        msg = c.get("message", "").lower()
        full_msg = c.get("message", "")
        if any(prefix.lower() in msg for prefix in _DECISION_COMMIT_PREFIXES):
            significant.append(c)
        elif "breaking change" in msg:
            significant.append(c)
    return significant[:50]  # cap at 50 to keep prompt size manageable


async def _extract_repo_entities(
    llm: LLMProvider,
    doc_content: str,
    repo_url: str,
    title: str,
) -> dict:
    """Extract architectural decisions and dependencies from README + docs."""
    prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/extract_repo.txt")
    try:
        with open(prompt_path) as f:
            template = f.read()
    except FileNotFoundError:
        return {}

    prompt = (
        template
        .replace("{content}", doc_content[:8000])
        .replace("{repo_url}", repo_url)
        .replace("{title}", title)
    )
    raw = await llm.generate(prompt, GenerateConfig(temperature=0.1, response_mime_type="application/json"))
    try:
        from app.services.ingestion_service import _clean_json
        return json.loads(_clean_json(raw or "{}"))
    except Exception:
        return {}


async def _extract_commit_decisions(
    llm: LLMProvider,
    commits: list[dict],
    repo_url: str,
    title: str,
) -> dict:
    """Extract decisions from significant commit messages."""
    prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/extract_commits.txt")
    try:
        with open(prompt_path) as f:
            template = f.read()
    except FileNotFoundError:
        return {}

    commit_log = "\n".join(
        f"[{c['sha']}] {c['date'][:10] if c.get('date') else ''} {c['author']}: {c['message'].splitlines()[0]}"
        for c in commits
    )
    prompt = (
        template
        .replace("{commits}", commit_log[:6000])
        .replace("{repo_url}", repo_url)
        .replace("{title}", title)
    )
    raw = await llm.generate(prompt, GenerateConfig(temperature=0.1, response_mime_type="application/json"))
    try:
        from app.services.ingestion_service import _clean_json
        return json.loads(_clean_json(raw or "{}"))
    except Exception:
        return {}


async def _upsert_repo_entities(
    graph: GraphService,
    llm: LLMProvider,
    entities: dict,
    repo_url: str,
    workspace: str,
    sensitivity: str,
    artifact_version_id: str,
) -> dict[str, int]:
    """Write all LLM-extracted repo entities into Neo4j. Returns entity counts."""
    counts: dict[str, int] = {}

    # Decisions (from README/docs or commits)
    decision_map: dict[str, str] = {}
    for d in entities.get("decisions", []):
        embedding = await llm.embed(f"{d.get('title', '')} {d.get('summary', '')}")
        did = await graph.upsert_decision(
            title=d.get("title", "Untitled"),
            summary=d.get("summary", ""),
            confidence=float(d.get("confidence", 0.75)),
            source_excerpt=d.get("source_excerpt", d.get("commit_sha", "")),
            embedding=embedding,
            workspace=workspace,
            tenant=workspace,
            confidentiality=sensitivity,
        )
        decision_map[d.get("title", "")] = did
    counts["decisions"] = len(decision_map)

    # ADRs → treated as decisions with explicit status
    _adr_status_map = {"accepted": "approved", "deprecated": "rejected", "superseded": "rejected", "proposed": "proposed"}
    for adr in entities.get("adrs", []):
        embedding = await llm.embed(f"{adr.get('title', '')} {adr.get('summary', '')}")
        status = _adr_status_map.get(adr.get("status", "proposed"), "proposed")
        did = await graph.upsert_decision(
            title=adr.get("title", "Untitled ADR"),
            summary=adr.get("summary", ""),
            status=status,
            confidence=0.9,
            source_excerpt=f"ADR status: {adr.get('status', 'proposed')}",
            embedding=embedding,
            workspace=workspace,
            tenant=workspace,
            confidentiality=sensitivity,
        )
        decision_map[adr.get("title", "")] = did
    counts["adrs"] = len(entities.get("adrs", []))

    # Assumptions
    for a in entities.get("assumptions", []):
        embedding = await llm.embed(a.get("text", ""))
        related_did = decision_map.get(a.get("related_decision_title", ""))
        await graph.upsert_assumption(
            text=a.get("text", ""),
            risk_level=a.get("risk_level", "medium"),
            decision_id=related_did,
            embedding=embedding,
            workspace=workspace,
            tenant=workspace,
            confidentiality=sensitivity,
        )
    counts["assumptions"] = len(entities.get("assumptions", []))

    # Requirements
    for r in entities.get("requirements", []):
        embedding = await llm.embed(f"{r.get('title', '')} {r.get('description', '')}")
        await graph.upsert_requirement_node(
            title=r.get("title", "Untitled Requirement"),
            description=r.get("description", ""),
            req_type=r.get("type", "functional"),
            priority=r.get("priority", "medium"),
            embedding=embedding,
            workspace=workspace,
            sensitivity=sensitivity,
            artifact_version_id=artifact_version_id,
        )
    counts["requirements"] = len(entities.get("requirements", []))

    # External dependencies → Evidence nodes (they evidence constraints / choices)
    for dep in entities.get("external_dependencies", []):
        name = dep.get("name", "")
        purpose = dep.get("purpose", "")
        version = dep.get("version") or ""
        embedding = await llm.embed(f"dependency {name} {purpose}")
        await graph.upsert_evidence(
            title=f"Dependency: {name}{' ' + version if version else ''}",
            content_summary=purpose,
            source_type="dependency",
            source_url=repo_url,
            embedding=embedding,
            workspace=workspace,
            tenant=workspace,
            confidentiality=sensitivity,
        )
    counts["dependencies"] = len(entities.get("external_dependencies", []))

    return counts
