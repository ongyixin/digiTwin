"""Graph analytics: blast radius, impact scoring, and centrality measures.

Uses APOC path expansion (available in the community docker-compose setup) as a
lightweight alternative to the GDS plugin. For enterprise deployments with GDS,
swap the APOC procedures for gds.pageRank and gds.betweenness.
"""

from neo4j import AsyncDriver

from app.models.api import ImpactScore


class AnalyticsService:
    def __init__(self, driver: AsyncDriver) -> None:
        self.driver = driver

    async def compute_impact(self, decision_id: str) -> ImpactScore:
        """Compute impact score and blast radius for a decision."""
        async with self.driver.session() as session:
            # Downstream dependency count (blast radius via BFS)
            result = await session.run(
                """
                MATCH (d:Decision {id: $id})
                OPTIONAL MATCH path = (d)-[:DEPENDS_ON|BLOCKS|REQUIRES_APPROVAL_FROM*1..5]->(downstream)
                RETURN
                    count(DISTINCT downstream) AS blast_radius
                """,
                id=decision_id,
            )
            row = (await result.single()) or {}
            blast_radius = row.get("blast_radius") or 0

            # Blocked tasks count
            result2 = await session.run(
                """
                MATCH (t:Task)-[:BLOCKS]->(d:Decision {id: $id})
                WHERE t.status = 'open'
                RETURN count(t) AS blocked_tasks
                """,
                id=decision_id,
            )
            row2 = (await result2.single()) or {}
            blocked_tasks = row2.get("blocked_tasks") or 0

            # Pending approvals count
            result3 = await session.run(
                """
                MATCH (ap:Approval {status: 'pending'})-[:FOR_DECISION]->(d:Decision {id: $id})
                RETURN count(ap) AS pending_approvals
                """,
                id=decision_id,
            )
            row3 = (await result3.single()) or {}
            pending_approvals = row3.get("pending_approvals") or 0

            # Downstream decisions that DEPEND_ON this one (transitively)
            result4 = await session.run(
                """
                MATCH (d:Decision {id: $id})<-[:DEPENDS_ON*1..4]-(dep:Decision)
                RETURN count(DISTINCT dep) AS downstream_decisions
                """,
                id=decision_id,
            )
            row4 = (await result4.single()) or {}
            downstream_decisions = row4.get("downstream_decisions") or 0

            # Central approvers (people who appear most in approval chains)
            result5 = await session.run(
                """
                MATCH (d:Decision {id: $id})-[:REQUIRES_APPROVAL_FROM]->(p:Person)
                RETURN p.name AS name
                LIMIT 5
                """,
                id=decision_id,
            )
            approver_rows = await result5.data()
            central_approvers = [r["name"] for r in approver_rows if r.get("name")]

        # Impact score: weighted sum normalized to 0–100
        raw_score = (
            blast_radius * 0.3
            + downstream_decisions * 0.4
            + blocked_tasks * 0.2
            + pending_approvals * 0.1
        )
        # Scale: cap at 100, log-scale for large graphs
        import math
        impact_score = round(min(100.0, math.log1p(raw_score) * 15), 1)

        return ImpactScore(
            decision_id=decision_id,
            impact_score=impact_score,
            blast_radius=blast_radius,
            downstream_decisions=downstream_decisions,
            blocked_tasks=blocked_tasks,
            pending_approvals=pending_approvals,
            central_approvers=central_approvers,
        )
