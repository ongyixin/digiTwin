from fastapi import APIRouter, Depends

from app.dependencies import get_driver
from app.models.api import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PolicySimulateRequest,
    PolicySimulateResponse,
)
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


@router.get("/user/{user_id}")
async def get_user_permissions(user_id: str, driver=Depends(get_driver)):
    service = PermissionService(driver)
    return await service.get_user_permissions(user_id)


@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    driver=Depends(get_driver),
):
    service = PermissionService(driver)
    return await service.check_permission(request.user_id, request.action, request.resource_id)


@router.post("/simulate", response_model=PolicySimulateResponse)
async def simulate_policy(
    request: PolicySimulateRequest,
    driver=Depends(get_driver),
):
    """Test a hypothetical permission change without modifying the graph."""
    service = PermissionService(driver)

    # Get current state
    original = await service.check_permission(
        request.user_id, request.action, request.resource_id
    )

    # Simulate hypothetical state using a rollback transaction
    simulated = await service.simulate_permission(
        user_id=request.user_id,
        action=request.action,
        resource_id=request.resource_id,
        hypothetical_grants=request.hypothetical_grants,
        hypothetical_delegations=request.hypothetical_delegations,
    )

    # Compute policy path diff
    orig_set = set(original.policy_path)
    sim_set = set(simulated.policy_path)
    policy_path_diff = [
        f"+ {p}" for p in sim_set - orig_set
    ] + [
        f"- {p}" for p in orig_set - sim_set
    ]

    return PolicySimulateResponse(
        original=original,
        simulated=simulated,
        policy_path_diff=policy_path_diff,
    )
