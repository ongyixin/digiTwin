from fastapi import APIRouter, Depends

from app.dependencies import get_driver, get_llm
from app.models.api import QueryRequest, QueryResponse
from app.services.chatbot_service import ChatbotService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api", tags=["chatbot"])


@router.post("/chatbot", response_model=QueryResponse)
async def chatbot(
    request: QueryRequest,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
):
    perm_svc = PermissionService(driver)
    user_perms = await perm_svc.get_user_permissions(request.user_id)
    allowed_scopes: list[str] | None = None
    scopes = [
        p.get("scope")
        for p in user_perms.get("permissions", [])
        if p.get("scope")
    ]
    if scopes:
        allowed_scopes = list(set(scopes))

    service = ChatbotService(driver, llm)
    return await service.chat(
        request.question,
        request.user_id,
        request.top_k,
        allowed_scopes=allowed_scopes,
    )
