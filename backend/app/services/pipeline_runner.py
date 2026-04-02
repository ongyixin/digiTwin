"""RocketRide pipeline execution bridge.

When ROCKETRIDE_URI and ROCKETRIDE_APIKEY are set, artifact ingestion is
delegated to the RocketRide engine via the Python SDK.  The engine executes
the portable .pipe DAGs (chunking → LLM → embed → Neo4j) and emits progress
events that are translated into the internal job-tracker protocol.

When RocketRide is not configured (ROCKETRIDE_URI empty) the module signals
unavailability via ``is_available() == False`` and callers fall back to the
existing in-process execution path — no behaviour change for local dev.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipe file resolution
# ---------------------------------------------------------------------------

def _pipelines_dir() -> Path:
    if settings.pipelines_dir:
        return Path(settings.pipelines_dir)
    # Auto-detect: workspace root is four levels up from this file
    # (.../backend/app/services/pipeline_runner.py → .../backend/app/services
    #  → .../backend/app → .../backend → .../workspace)
    return Path(__file__).parent.parent.parent.parent / "pipelines"


ARTIFACT_PIPE_MAP: dict[str, str] = {
    "transcript": "ingest_transcript.pipe",
    "prd": "ingest_prd.pipe",
    "rfc": "ingest_prd.pipe",
    "postmortem": "ingest_prd.pipe",
    "audio": "ingest_audio.pipe",
    "video": "ingest_audio.pipe",
    "github_repo": "ingest_repo.pipe",
    "policy_doc": "ingest_policy_doc.pipe",
    "generic_text": "ingest_policy_doc.pipe",
    "contract": "ingest_policy_doc.pipe",
}

# ---------------------------------------------------------------------------
# RocketRide event → internal job stage mapping
# ---------------------------------------------------------------------------

_NODE_TO_STAGE: dict[str, str] = {
    "chunker": "chunking",
    "section_splitter": "chunking",
    "entity_extractor": "entity_extraction",
    "architecture_extractor": "entity_extraction",
    "code_parser": "entity_extraction",
    "relationship_extractor": "relationship_extraction",
    "embedding_generator": "embedding",
    "neo4j_writer": "graph_upsert",
    "audit_emitter": "provenance",
    "transcriber": "transcription",
    "github_auth": "setup",
    "repo_enumerator": "setup",
    "pii_scan": "setup",
    "provenance_register": "provenance",
    "draft_messages": "entity_extraction",
    "layout_extractor": "chunking",
    "fetch_pending_approvals": "setup",
    "policy_check": "setup",
    "write_agent_action": "provenance",
}


async def _dispatch_rr_event(event: dict, job_emitter: Callable) -> None:
    """Translate a RocketRide server event into a job-tracker call."""
    body = event.get("body") or {}
    node_id: str = body.get("nodeId") or body.get("node_id", "")
    state: str = body.get("state", "")
    evt_type: str = event.get("event", "")

    stage = _NODE_TO_STAGE.get(node_id)
    if not stage:
        return

    entities: int = int(body.get("outputCount", 0) or body.get("entities_found", 0))

    try:
        if state == "started" or "node_started" in evt_type:
            await job_emitter("stage_started", stage=stage)
        elif state in ("completed", "finished") or "node_completed" in evt_type:
            await job_emitter("stage_completed", stage=stage, entities_found=entities)
    except Exception as exc:
        logger.debug("job_emitter dispatch error (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# PipelineRunner
# ---------------------------------------------------------------------------

class PipelineRunner:
    """Delegates pipeline execution to a running RocketRide engine.

    Usage::

        runner = get_pipeline_runner()
        if runner.is_available() and (pipe := runner.pipe_path_for("transcript")):
            result = await runner.run_pipe(pipe, payload, "transcript", job_emitter)
    """

    def is_available(self) -> bool:
        """True when both ROCKETRIDE_URI and ROCKETRIDE_APIKEY are configured."""
        return bool(settings.rocketride_uri and settings.rocketride_apikey)

    def pipe_path_for(self, artifact_type: str) -> Optional[str]:
        """Return the absolute path to the .pipe file for *artifact_type*, or None."""
        filename = ARTIFACT_PIPE_MAP.get(artifact_type)
        if not filename:
            return None
        path = _pipelines_dir() / filename
        return str(path) if path.exists() else None

    async def run_pipe(
        self,
        pipe_path: str,
        payload: dict[str, Any],
        artifact_type: str = "unknown",
        job_emitter: Optional[Callable] = None,
    ) -> dict[str, Any]:
        """Execute *pipe_path* on the RocketRide engine with *payload* as input.

        *payload* is serialised to JSON and delivered to the pipeline's source
        node as ``application/json``.  Progress events are forwarded to
        *job_emitter* when provided.

        Returns the pipeline result body dict (may be empty on some pipelines).
        Raises ``rocketride.RocketRideException`` subclasses on failure.
        """
        from rocketride import RocketRideClient  # local import keeps startup fast

        async def _on_event(event: dict) -> None:
            if job_emitter:
                await _dispatch_rr_event(event, job_emitter)

        data = json.dumps(payload).encode()

        logger.info(
            "RocketRide: running %s for artifact_type=%s payload_bytes=%d",
            pipe_path,
            artifact_type,
            len(data),
        )

        async with RocketRideClient(
            uri=settings.rocketride_uri,
            auth=settings.rocketride_apikey,
            on_event=_on_event,
            request_timeout=600_000,  # 10 min ceiling for large documents / LLM calls
        ) as client:
            result = await client.use(filepath=pipe_path)
            token: str = result["token"]

            await client.set_events(token, [
                "apaevt_status_processing",
                "apaevt_node_started",
                "apaevt_node_completed",
                "apaevt_status_upload",
            ])

            out = await client.send(
                token,
                data,
                objinfo={"name": f"{artifact_type}_payload.json"},
                mimetype="application/json",
            )
            await client.terminate(token)

        body: dict[str, Any] = {}
        if isinstance(out, dict):
            body = out.get("result", out)

        logger.info("RocketRide: %s completed — result keys: %s", pipe_path, list(body.keys()))
        return body

    async def run_policy_check(
        self,
        user_id: str,
        action: str,
        resource_id: str,
    ) -> dict[str, Any]:
        """Run check_policy.pipe and return the permission result.

        Falls back to ``{"allowed": True, ...}`` when RocketRide is not
        available so callers don't need to branch on availability.
        """
        if not self.is_available():
            return {
                "allowed": True,
                "policy_path": [],
                "requires_approval": False,
                "approver": None,
                "reason": "RocketRide not configured — policy check skipped",
            }

        pipe_path_obj = _pipelines_dir() / "check_policy.pipe"
        if not pipe_path_obj.exists():
            logger.warning("check_policy.pipe not found at %s", pipe_path_obj)
            return {"allowed": True, "policy_path": [], "requires_approval": False, "approver": None, "reason": "pipe not found"}

        return await self.run_pipe(
            str(pipe_path_obj),
            {"user_id": user_id, "action": action, "resource_id": resource_id},
            artifact_type="policy_check",
        )

    async def run_draft_followups(
        self,
        user_id: str,
        job_emitter: Optional[Callable] = None,
    ) -> dict[str, Any]:
        """Run draft_followups.pipe for the given *user_id*."""
        pipe_path_obj = _pipelines_dir() / "draft_followups.pipe"
        if not pipe_path_obj.exists():
            raise FileNotFoundError(f"draft_followups.pipe not found at {pipe_path_obj}")

        return await self.run_pipe(
            str(pipe_path_obj),
            {"user_id": user_id},
            artifact_type="draft_followups",
            job_emitter=job_emitter,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_runner: Optional[PipelineRunner] = None


def get_pipeline_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner()
    return _runner
