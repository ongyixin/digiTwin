"""Artifact management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_driver
from app.models.artifact import ArtifactRecord
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("", response_model=list[dict])
async def list_artifacts(
    workspace_id: str = Query(default="default"),
    artifact_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    driver=Depends(get_driver),
) -> list[dict]:
    """Return all non-archived ingested artifacts for a workspace."""
    service = GraphService(driver)
    return await service.list_artifacts(
        workspace_id=workspace_id,
        artifact_type=artifact_type,
        limit=limit,
    )


@router.get("/archived", response_model=list[dict])
async def list_archived_artifacts(
    workspace_id: str = Query(default="default"),
    artifact_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    driver=Depends(get_driver),
) -> list[dict]:
    """Return all archived artifacts for a workspace."""
    service = GraphService(driver)
    return await service.list_archived_artifacts(
        workspace_id=workspace_id,
        artifact_type=artifact_type,
        limit=limit,
    )


@router.post("/{artifact_id}/archive")
async def archive_artifact(
    artifact_id: str,
    driver=Depends(get_driver),
) -> dict:
    """Archive an artifact so it no longer appears in the main dashboard."""
    service = GraphService(driver)
    success = await service.archive_artifact(artifact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"success": True, "artifact_id": artifact_id}


@router.post("/{artifact_id}/unarchive")
async def unarchive_artifact(
    artifact_id: str,
    driver=Depends(get_driver),
) -> dict:
    """Restore an archived artifact back to the active list."""
    service = GraphService(driver)
    success = await service.unarchive_artifact(artifact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"success": True, "artifact_id": artifact_id}


@router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    driver=Depends(get_driver),
) -> dict:
    """Permanently delete an artifact and all its associated data."""
    service = GraphService(driver)
    success = await service.delete_artifact(artifact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"success": True, "artifact_id": artifact_id}


@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    driver=Depends(get_driver),
) -> dict:
    """Return a single artifact with its versions."""
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (a:Artifact {id: $id})
            OPTIONAL MATCH (a)-[:HAS_VERSION]->(av:ArtifactVersion)
            RETURN a,
                   collect({
                       id: av.id,
                       content_hash: av.content_hash,
                       ingested_at: av.ingested_at,
                       model_version: av.model_version
                   }) AS versions
            """,
            id=artifact_id,
        )
        row = await result.single()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {
        **{k: v for k, v in dict(row["a"]).items()},
        "versions": row["versions"],
    }


@router.get("/{artifact_id}/chunks")
async def get_artifact_chunks(
    artifact_id: str,
    limit: int = Query(default=20, le=100),
    driver=Depends(get_driver),
) -> list[dict]:
    """Return the text chunks for an artifact (without embeddings)."""
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (a:Artifact {id: $id})-[:HAS_VERSION]->(av:ArtifactVersion)
                  -[:CONTAINS_CHUNK]->(c:Chunk)
            RETURN c.id AS id, c.sequence AS sequence, c.text AS text
            ORDER BY av.ingested_at DESC, c.sequence ASC
            LIMIT $limit
            """,
            id=artifact_id,
            limit=limit,
        )
        return await result.data()


@router.get("/{artifact_id}/diff")
async def get_artifact_diff(
    artifact_id: str,
    driver=Depends(get_driver),
) -> dict:
    """Return a diff between the two most recent versions of an artifact.

    Shows new entities added, entities superseded, and cross-artifact
    contradictions or confirmations introduced by the latest version.
    """
    async with driver.session() as session:
        # Get the two most recent versions
        result = await session.run(
            """
            MATCH (a:Artifact {id: $id})-[:HAS_VERSION]->(av:ArtifactVersion)
            RETURN av.id AS version_id, av.ingested_at AS ingested_at,
                   av.content_hash AS content_hash
            ORDER BY av.ingested_at DESC LIMIT 2
            """,
            id=artifact_id,
        )
        versions = await result.data()

    if len(versions) < 2:
        return {
            "artifact_id": artifact_id,
            "has_diff": False,
            "message": "Only one version available — no diff to compute",
            "versions": versions,
        }

    latest = versions[0]
    previous = versions[1]

    async with driver.session() as session:
        # Entities created in the latest version window
        result = await session.run(
            """
            MATCH (n)
            WHERE (n:Decision OR n:Assumption OR n:Evidence OR n:Policy OR n:Requirement)
              AND n.created_at >= $since_ts
            RETURN labels(n)[0] AS label,
                   n.id AS id,
                   coalesce(n.title, n.text, n.id) AS title
            """,
            since_ts=previous["ingested_at"],
        )
        new_entities = await result.data()

        # Contradictions introduced since the previous version
        result2 = await session.run(
            """
            MATCH (a:Assumption)-[:CONTRADICTED_BY]->(e:Evidence)
            WHERE e.created_at >= $since_ts
            RETURN a.id AS assumption_id, a.text AS assumption_text,
                   e.title AS evidence_title, e.id AS evidence_id
            """,
            since_ts=previous["ingested_at"],
        )
        new_contradictions = await result2.data()

    return {
        "artifact_id": artifact_id,
        "has_diff": True,
        "latest_version": latest,
        "previous_version": previous,
        "new_entities": new_entities,
        "new_contradictions": new_contradictions,
        "summary": (
            f"{len(new_entities)} entities added, "
            f"{len(new_contradictions)} new contradictions since previous version"
        ),
    }
