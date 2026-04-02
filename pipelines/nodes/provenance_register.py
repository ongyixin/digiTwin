"""
RocketRide custom node: Register artifact provenance in Neo4j.

Actions:
  upsert_artifact_version  — create or update Artifact + ArtifactVersion nodes
"""

import hashlib
import json
import os
import sys
import uuid
from datetime import datetime

from neo4j import GraphDatabase


def get_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "digitwin2026")
    return GraphDatabase.driver(uri, auth=(user, password))


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def upsert_artifact_version(session, payload: dict) -> dict:
    artifact_id = payload.get("artifact_id") or _new_id("ART")
    artifact_type = payload.get("artifact_type", "unknown")
    source_type = payload.get("source_type", "upload")
    title = payload.get("title", "Untitled")
    workspace_id = payload.get("workspace_id", "default")
    sensitivity = payload.get("sensitivity", "internal")
    mime_type = payload.get("mime_type", "text/plain")
    content = payload.get("content", "")
    model_version = payload.get("model_version", os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))

    content_hash = _content_hash(content) if content else _new_id("H")
    version_id = _new_id("AV")
    now = datetime.utcnow().isoformat()

    session.run(
        """
        MERGE (a:Artifact {id: $id})
        SET a.artifact_type = $artifact_type,
            a.source_type   = $source_type,
            a.title         = $title,
            a.workspace_id  = $workspace_id,
            a.sensitivity   = $sensitivity,
            a.mime_type     = $mime_type,
            a.updated_at    = $now
        """,
        id=artifact_id,
        artifact_type=artifact_type,
        source_type=source_type,
        title=title,
        workspace_id=workspace_id,
        sensitivity=sensitivity,
        mime_type=mime_type,
        now=now,
    )

    session.run(
        """
        MERGE (av:ArtifactVersion {id: $id})
        SET av.artifact_id    = $artifact_id,
            av.content_hash   = $content_hash,
            av.model_version  = $model_version,
            av.ingested_at    = $now
        WITH av
        MATCH (a:Artifact {id: $artifact_id})
        MERGE (a)-[:HAS_VERSION]->(av)
        """,
        id=version_id,
        artifact_id=artifact_id,
        content_hash=content_hash,
        model_version=model_version,
        now=now,
    )

    return {
        "artifact_id": artifact_id,
        "artifact_version_id": version_id,
        "status": "ok",
    }


def main() -> None:
    payload = json.loads(sys.stdin.read())
    action = payload.get("action", "upsert_artifact_version")

    driver = get_driver()
    with driver.session() as session:
        if action == "upsert_artifact_version":
            result = upsert_artifact_version(session, payload)
        else:
            raise ValueError(f"Unknown action: {action}")

    print(json.dumps(result))
    driver.close()


if __name__ == "__main__":
    main()
