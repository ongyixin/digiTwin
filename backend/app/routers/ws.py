"""WebSocket endpoint for real-time pipeline job progress."""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import job_service

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/jobs/{job_id}")
async def job_progress(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()

    job = job_service.get_job(job_id)
    if not job:
        await websocket.send_text(json.dumps({"type": "error", "message": "Job not found"}))
        await websocket.close()
        return

    # Send current state immediately so clients joining late get a snapshot
    await websocket.send_text(json.dumps({
        "type": "job_snapshot",
        "job": job.model_dump(),
    }))

    # If already done, close after snapshot
    if job.status in ("completed", "failed"):
        await websocket.close()
        return

    q = job_service.subscribe(job_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                await websocket.send_text(json.dumps(event, default=str))
                if event.get("type") in ("job_completed", "job_failed"):
                    break
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        job_service.unsubscribe(job_id, q)
        try:
            await websocket.close()
        except Exception:
            pass
