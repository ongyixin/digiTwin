"""Permission resolution via Neo4j graph traversal."""

from typing import Any

from neo4j import AsyncDriver

from app.models.api import HypotheticalDelegation, HypotheticalGrant, PermissionCheckResponse


class PermissionService:
    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    async def check_permission(
        self, user_id: str, action: str, resource_id: str
    ) -> PermissionCheckResponse:
        async with self.driver.session() as session:
            # Direct role-based permission check
            result = await session.run(
                """
                MATCH (p:Person {id: $user_id})
                MATCH (p)-[:HAS_ROLE]->(r:Role)-[:GRANTS]->(perm:Permission {action: $action})
                MATCH (perm)-[:ON_RESOURCE]->(res:Resource {id: $resource_id})
                RETURN r.name AS role, perm.action AS action, perm.conditions AS conditions
                LIMIT 1
                """,
                user_id=user_id, action=action, resource_id=resource_id,
            )
            direct = await result.data()

            if direct:
                row = direct[0]
                return PermissionCheckResponse(
                    allowed=True,
                    policy_path=[f"User:{user_id}", f"Role:{row['role']}", f"Permission:{action}", f"Resource:{resource_id}"],
                    reason=f"Allowed via role '{row['role']}'",
                )

            # Delegated permission check
            result = await session.run(
                """
                MATCH (p:Person {id: $user_id})<-[:DELEGATED_TO]-(delegator:Person)
                MATCH (delegator)-[:HAS_ROLE]->(r:Role)-[:GRANTS]->(perm:Permission {action: $action})
                MATCH (perm)-[:ON_RESOURCE]->(res:Resource {id: $resource_id})
                RETURN delegator.name AS delegator_name, r.name AS role
                LIMIT 1
                """,
                user_id=user_id, action=action, resource_id=resource_id,
            )
            delegated = await result.data()

            if delegated:
                row = delegated[0]
                return PermissionCheckResponse(
                    allowed=True,
                    policy_path=[
                        f"User:{user_id}",
                        f"DelegatedBy:{row['delegator_name']}",
                        f"Role:{row['role']}",
                        f"Permission:{action}",
                        f"Resource:{resource_id}",
                    ],
                    reason=f"Allowed via delegation from '{row['delegator_name']}'",
                )

            # Check if approval is required
            result = await session.run(
                """
                MATCH (res:Resource {id: $resource_id})<-[:REQUIRES_APPROVAL]-(perm:Permission {action: $action})
                MATCH (perm)<-[:GRANTS]-(r:Role)-[:HAS_APPROVER]->(approver:Person)
                RETURN approver.id AS approver_id, approver.name AS approver_name
                LIMIT 1
                """,
                resource_id=resource_id, action=action,
            )
            approval_needed = await result.data()

            if approval_needed:
                row = approval_needed[0]
                return PermissionCheckResponse(
                    allowed=False,
                    policy_path=[f"User:{user_id}", f"Resource:{resource_id}", "RequiresApproval"],
                    requires_approval=True,
                    approver=row["approver_name"],
                    reason=f"Action '{action}' on this resource requires approval from {row['approver_name']}",
                )

        return PermissionCheckResponse(
            allowed=False,
            policy_path=[f"User:{user_id}", f"Action:{action}", f"Resource:{resource_id}", "Denied"],
            reason=f"No permission found for action '{action}' on resource '{resource_id}'",
        )

    async def get_user_permissions(self, user_id: str) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Person {id: $user_id})
                OPTIONAL MATCH (p)-[:HAS_ROLE]->(r:Role)
                OPTIONAL MATCH (r)-[:GRANTS]->(perm:Permission)
                OPTIONAL MATCH (perm)-[:ON_RESOURCE]->(res:Resource)
                OPTIONAL MATCH (perm)-[:WITHIN_SCOPE]->(scope:Scope)
                RETURN p.name AS name,
                       collect(DISTINCT r.name) AS roles,
                       collect(DISTINCT {action: perm.action, resource: res.id, scope: scope.name}) AS permissions
                """,
                user_id=user_id,
            )
            data = await result.data()

        if not data:
            return {"user_id": user_id, "name": "Unknown", "roles": [], "permissions": []}

        row = data[0]
        return {
            "user_id": user_id,
            "name": row["name"],
            "roles": [r for r in row["roles"] if r],
            "permissions": [p for p in row["permissions"] if p.get("action") and p.get("resource")],
        }

    async def can_user_send_reminder(self, user_id: str) -> bool:
        result = await self.check_permission(user_id, "execute", "send-reminder")
        return result.allowed

    async def can_user_escalate(self, user_id: str) -> bool:
        result = await self.check_permission(user_id, "execute", "escalate")
        return result.allowed

    async def simulate_permission(
        self,
        user_id: str,
        action: str,
        resource_id: str,
        hypothetical_grants: list[HypotheticalGrant] | None = None,
        hypothetical_delegations: list[HypotheticalDelegation] | None = None,
    ) -> PermissionCheckResponse:
        """Run a permission check inside a rolled-back transaction to test hypotheticals.

        Creates temporary Role/Permission/Delegation nodes in a transaction,
        checks permissions, then rolls back — leaving the graph unchanged.
        """
        async with self.driver.session() as session:
            async with await session.begin_transaction() as tx:
                # Apply hypothetical grants as temporary Role nodes
                for grant in (hypothetical_grants or []):
                    await tx.run(
                        """
                        MERGE (p:Person {id: $user_id})
                        MERGE (r:Role {id: $role_id, name: $role_name})
                        MERGE (res:Resource {id: $resource_id})
                        MERGE (perm:Permission {id: $perm_id, action: $action})
                        MERGE (perm)-[:ON_RESOURCE]->(res)
                        MERGE (r)-[:GRANTS]->(perm)
                        MERGE (p)-[:HAS_ROLE]->(r)
                        """,
                        user_id=grant.user_id,
                        role_id=f"hyp_role_{grant.role}",
                        role_name=grant.role,
                        resource_id=grant.resource_id or resource_id,
                        perm_id=f"hyp_perm_{action}_{grant.resource_id or resource_id}",
                        action=action,
                    )

                # Apply hypothetical delegations
                for delegation in (hypothetical_delegations or []):
                    await tx.run(
                        """
                        MERGE (from:Person {id: $from_id})
                        MERGE (to:Person {id: $to_id})
                        MERGE (from)-[:DELEGATED_TO]->(to)
                        """,
                        from_id=delegation.from_user_id,
                        to_id=delegation.to_user_id,
                    )

                # Run permission check within the transaction
                result = await tx.run(
                    """
                    MATCH (p:Person {id: $user_id})
                    MATCH (p)-[:HAS_ROLE]->(r:Role)-[:GRANTS]->(perm:Permission {action: $action})
                    MATCH (perm)-[:ON_RESOURCE]->(res:Resource {id: $resource_id})
                    RETURN r.name AS role, perm.action AS action
                    LIMIT 1
                    """,
                    user_id=user_id, action=action, resource_id=resource_id,
                )
                direct = await result.data()

                if direct:
                    row = direct[0]
                    response = PermissionCheckResponse(
                        allowed=True,
                        policy_path=[
                            f"User:{user_id}",
                            f"Role:{row['role']}",
                            f"Permission:{action}",
                            f"Resource:{resource_id}",
                            "(hypothetical)",
                        ],
                        reason=f"Hypothetically allowed via role '{row['role']}'",
                    )
                else:
                    response = PermissionCheckResponse(
                        allowed=False,
                        policy_path=[f"User:{user_id}", f"Action:{action}", f"Resource:{resource_id}", "Denied(hypothetical)"],
                        reason=f"No permission found even with hypothetical grants",
                    )

                # Rollback: discard all hypothetical changes
                await tx.rollback()

        return response
