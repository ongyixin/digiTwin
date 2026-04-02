"""In-memory job store and progress tracking for ingestion pipelines.

Each ingestion job gets a unique ID, progresses through named pipeline stages,
and emits events to connected WebSocket clients in real time.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from app.models.api import JobState, JobStatus, StageInfo, StageStatus, TwinDiff


# Global in-memory job store (keyed by job_id)
_jobs: dict[str, JobState] = {}

# Per-job subscriber queues: job_id -> list of asyncio.Queue
_subscribers: dict[str, list[asyncio.Queue]] = {}

# Default transcript pipeline stages (kept for backward compatibility)
PIPELINE_STAGES = [
    "setup",
    "chunking",
    "entity_extraction",
    "relationship_extraction",
    "embedding",
    "graph_upsert",
    "twin_diff",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(
    job_id: str,
    artifact_title: str,
    artifact_type: str = "transcript",
    stages: Optional[list[str]] = None,
    # legacy parameter kept for backward compat
    meeting_title: Optional[str] = None,
) -> JobState:
    title = artifact_title or meeting_title or "Untitled"
    stage_list = stages or PIPELINE_STAGES
    state = JobState(
        job_id=job_id,
        status=JobStatus.queued,
        artifact_title=title,
        artifact_type=artifact_type,
        # legacy field — keep in sync
        meeting_title=title,
        created_at=_now(),
        stages=[StageInfo(name=s) for s in stage_list],
    )
    _jobs[job_id] = state
    _subscribers[job_id] = []
    return state


def get_job(job_id: str) -> Optional[JobState]:
    return _jobs.get(job_id)


def list_jobs(limit: int = 20) -> list[JobState]:
    jobs = sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)
    return jobs[:limit]


def subscribe(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(job_id, []).append(q)
    return q


def unsubscribe(job_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(job_id, [])
    if q in subs:
        subs.remove(q)


async def _broadcast(job_id: str, event: dict) -> None:
    for q in list(_subscribers.get(job_id, [])):
        await q.put(event)


def _get_stage(state: JobState, stage_name: str) -> Optional[StageInfo]:
    for s in state.stages:
        if s.name == stage_name:
            return s
    return None


async def mark_running(job_id: str) -> None:
    state = _jobs.get(job_id)
    if not state:
        return
    state.status = JobStatus.running
    await _broadcast(job_id, {"type": "job_started", "job_id": job_id, "ts": _now()})


async def stage_started(job_id: str, stage: str, detail: str = "") -> None:
    state = _jobs.get(job_id)
    if not state:
        return
    s = _get_stage(state, stage)
    if s:
        s.status = StageStatus.running
        s.started_at = _now()
        s.detail = detail or None
    await _broadcast(job_id, {
        "type": "stage_started",
        "stage": stage,
        "detail": detail,
        "ts": _now(),
    })


async def stage_completed(job_id: str, stage: str, entities_found: int = 0) -> None:
    state = _jobs.get(job_id)
    if not state:
        return
    s = _get_stage(state, stage)
    if s:
        s.status = StageStatus.completed
        s.completed_at = _now()
        s.entities_found = entities_found
        if s.started_at:
            start = datetime.fromisoformat(s.started_at)
            end = datetime.fromisoformat(s.completed_at)
            s.duration_ms = int((end - start).total_seconds() * 1000)
    await _broadcast(job_id, {
        "type": "stage_completed",
        "stage": stage,
        "entities_found": entities_found,
        "duration_ms": s.duration_ms if s else None,
        "ts": _now(),
    })


async def mark_completed(
    job_id: str,
    entities_created: dict[str, int],
    twin_diff: Optional[TwinDiff],
    meeting_id: Optional[str],
) -> None:
    state = _jobs.get(job_id)
    if not state:
        return
    state.status = JobStatus.completed
    state.completed_at = _now()
    state.entities_created = entities_created
    state.twin_diff = twin_diff
    state.meeting_id = meeting_id
    await _broadcast(job_id, {
        "type": "job_completed",
        "job_id": job_id,
        "entities_created": entities_created,
        "twin_diff": twin_diff.model_dump() if twin_diff else None,
        "ts": _now(),
    })


async def mark_failed(job_id: str, error: str) -> None:
    state = _jobs.get(job_id)
    if not state:
        return
    state.status = JobStatus.failed
    state.error = error
    state.completed_at = _now()
    for s in state.stages:
        if s.status == StageStatus.running:
            s.status = StageStatus.failed
    await _broadcast(job_id, {
        "type": "job_failed",
        "job_id": job_id,
        "error": error,
        "ts": _now(),
    })


def make_emitter(job_id: str) -> Callable:
    """Return an async callable that routes ingestion events to job_service."""

    async def _emit(event: str, stage: str = "", detail: str = "", entities_found: int = 0, **_: Any) -> None:
        if event == "stage_started":
            await stage_started(job_id, stage, detail)
        elif event == "stage_completed":
            await stage_completed(job_id, stage, entities_found)

    return _emit
