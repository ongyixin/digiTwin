"""In-memory event store and broadcasting for resolution case live updates.

Mirrors the pattern from job_service.py for WebSocket streaming.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any


# Per-case subscriber queues: case_id -> list of asyncio.Queue
_subscribers: dict[str, list[asyncio.Queue]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def subscribe(case_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(case_id, []).append(q)
    return q


def unsubscribe(case_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(case_id, [])
    if q in subs:
        subs.remove(q)


async def broadcast(case_id: str, event: dict[str, Any]) -> None:
    for q in list(_subscribers.get(case_id, [])):
        await q.put(event)


async def emit_case_created(case_id: str, title: str) -> None:
    await broadcast(case_id, {
        "type": "case_created",
        "case_id": case_id,
        "title": title,
        "ts": _now(),
    })


async def emit_plan_generated(case_id: str, plan_id: str, action_count: int) -> None:
    await broadcast(case_id, {
        "type": "plan_generated",
        "case_id": case_id,
        "plan_id": plan_id,
        "action_count": action_count,
        "ts": _now(),
    })


async def emit_action_allowed(case_id: str, action_id: str, action_type: str) -> None:
    await broadcast(case_id, {
        "type": "action_allowed",
        "case_id": case_id,
        "action_id": action_id,
        "action_type": action_type,
        "ts": _now(),
    })


async def emit_action_blocked(case_id: str, action_id: str, action_type: str, reason: str) -> None:
    await broadcast(case_id, {
        "type": "action_blocked",
        "case_id": case_id,
        "action_id": action_id,
        "action_type": action_type,
        "reason": reason,
        "ts": _now(),
    })


async def emit_action_executed(case_id: str, action_id: str, action_type: str) -> None:
    await broadcast(case_id, {
        "type": "action_executed",
        "case_id": case_id,
        "action_id": action_id,
        "action_type": action_type,
        "ts": _now(),
    })


async def emit_review_requested(case_id: str, action_id: str, action_type: str) -> None:
    await broadcast(case_id, {
        "type": "review_requested",
        "case_id": case_id,
        "action_id": action_id,
        "action_type": action_type,
        "ts": _now(),
    })


async def emit_case_resolved(case_id: str) -> None:
    await broadcast(case_id, {
        "type": "case_resolved",
        "case_id": case_id,
        "ts": _now(),
    })
