"""Evaluation: permission correctness.

Tests that the permission system correctly allows/denies actions for
a known set of user/action/resource triples.

Run with: pytest tests/eval/permission_correctness.py -v
Requires a running Neo4j instance with the demo permission graph seeded.
"""

import asyncio
import pytest
from typing import Optional


PERMISSION_TEST_CASES = [
    # (user_id, action, resource_id, expected_allowed, notes)
    ("alex", "execute", "send-reminder", True, "Alex is PM, should be allowed"),
    ("alex", "execute", "escalate", True, "Alex has escalate permission"),
    ("unknown_user_xyz", "execute", "send-reminder", False, "Unknown user must be denied"),
    ("alex", "delete", "all-decisions", False, "Delete is not a valid action for any role"),
]


@pytest.mark.parametrize(
    "user_id,action,resource_id,expected_allowed,notes",
    PERMISSION_TEST_CASES,
    ids=[f"{c[0]}-{c[1]}-{c[2]}" for c in PERMISSION_TEST_CASES],
)
def test_permission_check(user_id: str, action: str, resource_id: str, expected_allowed: bool, notes: str):
    """Permission checks must match expected allow/deny for known user/action/resource triples."""
    try:
        from app.dependencies import get_neo4j_driver
        from app.services.permission_service import PermissionService
    except ImportError:
        pytest.skip("App dependencies not available")

    driver = get_neo4j_driver()
    service = PermissionService(driver)

    async def _run():
        return await service.check_permission(user_id, action, resource_id)

    result = asyncio.run(_run())
    assert result.allowed == expected_allowed, (
        f"[{notes}] Expected allowed={expected_allowed}, got allowed={result.allowed}. "
        f"Policy path: {result.policy_path}"
    )


def test_policy_path_is_non_empty_for_allowed():
    """Allowed permission checks must include a non-empty policy path for auditability."""
    try:
        from app.dependencies import get_neo4j_driver
        from app.services.permission_service import PermissionService
    except ImportError:
        pytest.skip("App dependencies not available")

    driver = get_neo4j_driver()
    service = PermissionService(driver)

    async def _run():
        return await service.check_permission("alex", "execute", "send-reminder")

    result = asyncio.run(_run())
    if result.allowed:
        assert len(result.policy_path) > 0, (
            "Allowed permission must have a non-empty policy_path for audit"
        )
