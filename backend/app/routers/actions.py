from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_driver, get_llm
from app.models.api import (
    AgentActionResponse,
    DraftFollowupRequest,
    DraftFollowupResponse,
    ReviewDecision,
    ReviewTask,
)
from app.services.execution_service import ExecutionService
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("/draft-followups", response_model=DraftFollowupResponse)
async def draft_followups(
    request: DraftFollowupRequest,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    service = ExecutionService(driver, llm)
    return await service.draft_followups(request.user_id, request.decision_id)


@router.get("/history", response_model=list[AgentActionResponse])
async def action_history(driver=Depends(get_driver)):
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (aa:AgentAction)
            RETURN aa ORDER BY aa.timestamp DESC LIMIT 50
            """
        )
        data = await result.data()
    return [dict(r["aa"]) for r in data]


@router.get("/review-inbox", response_model=list[ReviewTask])
async def review_inbox(driver=Depends(get_driver)):
    graph = GraphService(driver)
    return await graph.get_review_inbox()


@router.post("/review/{task_id}/approve")
async def resolve_review(
    task_id: str,
    decision: ReviewDecision,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    """Approve or reject a review task. On approval, re-runs the draft_followups pipeline."""
    graph = GraphService(driver)
    await graph.resolve_review_task(task_id, decision.approved, decision.reviewer_id)

    if decision.approved:
        # Re-run the original action with updated permissions (reviewer acts as the initiator)
        service = ExecutionService(driver, llm)
        result = await service.draft_followups(decision.reviewer_id)
        return {"success": True, "re_run_action_id": result.agent_action_id}

    return {"success": True, "action": "rejected"}
