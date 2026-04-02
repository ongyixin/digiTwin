"""Autonomous Resolution Engine API endpoints and WebSocket stream."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.dependencies import get_driver, get_llm
from app.models.resolution import (
    CreateCaseRequest,
    ResolutionCaseDetail,
    ResolutionCaseListItem,
    ResolutionCaseResponse,
    ReviewActionRequest,
)
from app.services import resolution_event_service as events
from app.services.resolution_service import ResolutionService

router = APIRouter(prefix="/api/resolution", tags=["resolution"])


@router.post("/resolve", response_model=ResolutionCaseResponse)
async def create_resolution_case(
    request: CreateCaseRequest,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    """Manually trigger a resolution case for a target entity."""
    service = ResolutionService(driver, llm)
    case_id = await service.create_case(
        target_type=request.target_type,
        target_id=request.target_id,
        requested_by=request.requested_by,
        autonomy_mode=request.autonomy_mode.value,
    )

    # Kick off plan generation in the background
    asyncio.create_task(service.run_resolution(case_id, request.requested_by))

    return ResolutionCaseResponse(case_id=case_id, status="planning")


@router.get("/cases", response_model=list[ResolutionCaseListItem])
async def list_resolution_cases(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    """List all resolution cases with optional filtering."""
    service = ResolutionService(driver, llm)
    cases = await service.list_cases(
        status=status,
        severity=severity,
        case_type=case_type,
        limit=limit,
    )
    return [
        ResolutionCaseListItem(
            case_id=c.get("id", ""),
            title=c.get("title", ""),
            case_type=c.get("case_type", "dependency_cluster"),
            status=c.get("status", "open"),
            severity=c.get("severity", "medium"),
            autonomy_mode=c.get("autonomy_mode", "recommend"),
            created_at=c.get("created_at", ""),
        )
        for c in cases
    ]


@router.get("/cases/{case_id}")
async def get_resolution_case(
    case_id: str,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    """Get full detail for a resolution case."""
    service = ResolutionService(driver, llm)
    detail = await service.get_case(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return detail


@router.post("/cases/{case_id}/actions/{action_id}/review")
async def review_proposed_action(
    case_id: str,
    action_id: str,
    request: ReviewActionRequest,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    """Approve or reject a proposed action."""
    service = ResolutionService(driver, llm)
    await service.review_action(
        case_id=case_id,
        action_id=action_id,
        reviewed_by=request.reviewed_by,
        decision=request.decision,
        comment=request.comment,
    )
    return {"success": True}


@router.post("/cases/{case_id}/actions/{action_id}/execute")
async def execute_proposed_action(
    case_id: str,
    action_id: str,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    """Execute a proposed action that has been approved."""
    service = ResolutionService(driver, llm)
    await service.execute_reviewed_action(case_id=case_id, action_id=action_id)
    return {"success": True}


@router.post("/cases/{case_id}/stop")
async def stop_resolution_case(
    case_id: str,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    """Cancel a resolution case."""
    service = ResolutionService(driver, llm)
    await service.stop_case(case_id)
    return {"success": True}


@router.websocket("/ws/{case_id}")
async def resolution_stream(websocket: WebSocket, case_id: str) -> None:
    """WebSocket endpoint for live resolution case events."""
    await websocket.accept()

    q = events.subscribe(case_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                await websocket.send_text(json.dumps(event, default=str))
                if event.get("type") == "case_resolved":
                    break
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        events.unsubscribe(case_id, q)
        try:
            await websocket.close()
        except Exception:
            pass
