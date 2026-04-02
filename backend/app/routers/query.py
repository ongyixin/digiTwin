from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import get_driver, get_llm
from app.models.api import QueryRequest, QueryResponse
from app.services.permission_service import PermissionService
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/api", tags=["query"])


class ArtifactQueryRequest(QueryRequest):
    """Extended query request with artifact-aware filters."""

    artifact_types: Optional[list[str]] = None
    sensitivity_ceiling: Optional[str] = None
    ingested_after: Optional[str] = None
    ingested_before: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def query(
    request: ArtifactQueryRequest,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    # Resolve the user's allowed scopes/workspaces for permission-scoped retrieval
    perm_svc = PermissionService(driver)
    user_perms = await perm_svc.get_user_permissions(request.user_id)
    allowed_scopes: list[str] | None = None

    # If we have explicit scopes on permissions, filter by them
    scopes = [
        p.get("scope")
        for p in user_perms.get("permissions", [])
        if p.get("scope")
    ]
    if scopes:
        allowed_scopes = list(set(scopes))

    service = RetrievalService(driver, llm)
    return await service.query(
        request.question,
        request.user_id,
        request.top_k,
        allowed_scopes=allowed_scopes,
        artifact_types=request.artifact_types,
        sensitivity_ceiling=request.sensitivity_ceiling,
        ingested_after=request.ingested_after,
        ingested_before=request.ingested_before,
    )
