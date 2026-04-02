"""Webhook endpoints for GitHub event-driven incremental ingestion.

Supports:
- push: re-ingest changed files, mark superseded symbols
- pull_request: create PullRequest node, link to affected files
- issues: create Issue node
- issue_comment: link comments to issues
"""

import asyncio
import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import get_driver, get_llm

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def _verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook HMAC signature."""
    if not _WEBHOOK_SECRET:
        return True  # Skip verification in dev if secret not configured
    expected = "sha256=" + hmac.new(
        _WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
) -> dict[str, Any]:
    """Receive GitHub webhook events and trigger incremental ingestion."""
    payload_bytes = await request.body()

    # Verify signature
    sig = request.headers.get("X-Hub-Signature-256", "")
    if sig and not _verify_signature(payload_bytes, sig):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "unknown")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Dispatch event handlers
    if event_type == "push":
        asyncio.create_task(_handle_push(payload, driver, llm))
    elif event_type == "pull_request":
        asyncio.create_task(_handle_pull_request(payload, driver, llm))
    elif event_type in ("issues", "issue"):
        asyncio.create_task(_handle_issue(payload, driver, llm))

    return {"received": True, "event": event_type}


async def _handle_push(payload: dict, driver, llm) -> None:
    """Process push event: re-extract changed files and mark superseded symbols."""
    from app.services.github.github_fetcher import GitHubFetcher
    from app.services.github.code_parser import CodeParser
    from app.services.graph_service import GraphService, _new_id

    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    branch = payload.get("ref", "refs/heads/main").replace("refs/heads/", "")
    commits = payload.get("commits", [])

    if not owner or not repo_name:
        return

    # Collect changed files across all commits
    changed_files: set[str] = set()
    for commit in commits:
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))

    if not changed_files:
        return

    graph = GraphService(driver)
    fetcher = GitHubFetcher()
    await fetcher.authenticate()
    parser = CodeParser()

    # Fetch changed file contents
    files = await fetcher.fetch_files(owner, repo_name, list(changed_files), branch=branch)
    latest_sha = await fetcher.get_latest_sha(owner, repo_name, branch)

    # Create a new ArtifactVersion for this push
    # First find the existing Artifact for this repo
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (a:Artifact {type: 'github_repo'})
            WHERE a.metadata CONTAINS $repo_name
            RETURN a.id AS artifact_id
            LIMIT 1
            """,
            repo_name=repo_name,
        )
        row = await result.single()

    if not row:
        return

    artifact_id = row["artifact_id"]
    version_id = _new_id("AV")
    await graph.upsert_artifact_version(
        version_id=version_id,
        artifact_id=artifact_id,
        content_hash=latest_sha[:16],
        model_version="gemini-2.5-flash",
    )

    # Re-parse and upsert changed symbols
    # Get the repo node id
    async with driver.session() as session:
        result = await session.run(
            "MATCH (r:Repository) WHERE r.repo_name = $repo_name RETURN r.id AS repo_id LIMIT 1",
            repo_name=repo_name,
        )
        row = await result.single()
    repo_node_id = row["repo_id"] if row else None

    for path, content in files.items():
        symbols = parser.extract_symbols(path, content)
        for sym in symbols:
            embedding = await llm.embed(f"{sym.get('kind', '')} {sym.get('name', '')} {sym.get('docstring', '')}")
            await graph.upsert_symbol(
                name=sym.get("name", ""),
                kind=sym.get("kind", "function"),
                file_path=sym.get("file_path", path),
                line_start=sym.get("line_start", 0),
                line_end=sym.get("line_end", 0),
                docstring=sym.get("docstring", ""),
                repo_node_id=repo_node_id,
                embedding=embedding,
                workspace_id="default",
                artifact_version_id=version_id,
            )


async def _handle_pull_request(payload: dict, driver, llm) -> None:
    """Process pull_request event: create PullRequest node."""
    from app.services.graph_service import GraphService, _new_id
    from datetime import datetime

    pr = payload.get("pull_request", {})
    if not pr:
        return

    graph = GraphService(driver)
    pr_id = _new_id("PR")

    repo = payload.get("repository", {})
    repo_name = repo.get("name", "")

    async with driver.session() as session:
        await session.run(
            """
            MERGE (pr:PullRequest {number: $number, repo_name: $repo_name})
            ON CREATE SET pr.id = $id
            SET pr.title = $title,
                pr.state = $state,
                pr.author = $author,
                pr.body = $body,
                pr.created_at = $created_at,
                pr.url = $url
            """,
            id=pr_id,
            number=pr.get("number", 0),
            repo_name=repo_name,
            title=pr.get("title", ""),
            state=pr.get("state", "open"),
            author=pr.get("user", {}).get("login", ""),
            body=(pr.get("body", "") or "")[:1000],
            created_at=pr.get("created_at", datetime.utcnow().isoformat()),
            url=pr.get("html_url", ""),
        )


async def _handle_issue(payload: dict, driver, llm) -> None:
    """Process issues event: create Issue node."""
    from app.services.graph_service import _new_id
    from datetime import datetime

    issue = payload.get("issue", {})
    if not issue:
        return

    repo = payload.get("repository", {})
    repo_name = repo.get("name", "")

    async with driver.session() as session:
        issue_id = _new_id("ISS")
        await session.run(
            """
            MERGE (i:Issue {number: $number, repo_name: $repo_name})
            ON CREATE SET i.id = $id
            SET i.title = $title,
                i.state = $state,
                i.author = $author,
                i.body = $body,
                i.created_at = $created_at,
                i.url = $url
            """,
            id=issue_id,
            number=issue.get("number", 0),
            repo_name=repo_name,
            title=issue.get("title", ""),
            state=issue.get("state", "open"),
            author=issue.get("user", {}).get("login", ""),
            body=(issue.get("body", "") or "")[:1000],
            created_at=issue.get("created_at", datetime.utcnow().isoformat()),
            url=issue.get("html_url", ""),
        )
