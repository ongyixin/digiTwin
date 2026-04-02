"""Core orchestrator for the Autonomous Resolution Engine."""

from datetime import datetime, timezone
from typing import Any, Optional

from neo4j import AsyncDriver

from app.llm.base import LLMProvider
from app.services import resolution_event_service as events
from app.services.graph_service import GraphService, _new_id
from app.services.planner_service import PlannerService
from app.services.risk_service import RiskService


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResolutionService:
    def __init__(self, driver: AsyncDriver, llm: LLMProvider):
        self.driver = driver
        self.llm = llm
        self.graph = GraphService(driver)
        self.planner = PlannerService(driver, llm)
        self.risk = RiskService(driver)

    # ------------------------------------------------------------------
    # Case lifecycle
    # ------------------------------------------------------------------

    async def create_case(
        self,
        target_type: str,
        target_id: str,
        requested_by: str,
        autonomy_mode: str,
    ) -> str:
        """Create a ResolutionCase, attach to target, compute initial risk."""
        case_id = _new_id("RC")

        # Fetch target to derive title and case type
        title, case_type = await self._derive_case_metadata(target_type, target_id)

        # Initial severity before full scoring
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (rc:ResolutionCase {id: $case_id})
                SET rc.title = $title,
                    rc.description = $description,
                    rc.case_type = $case_type,
                    rc.status = 'planning',
                    rc.severity = 'medium',
                    rc.autonomy_mode = $autonomy_mode,
                    rc.created_at = $created_at,
                    rc.created_by = $created_by,
                    rc.trigger_source = 'manual',
                    rc.workspace_id = 'default'
                WITH rc
                OPTIONAL MATCH (target {id: $target_id})
                FOREACH (_ IN CASE WHEN target IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (rc)-[:ABOUT]->(target)
                )
                """,
                case_id=case_id,
                title=title,
                description=f"Resolution case for {target_type} {target_id}",
                case_type=case_type,
                autonomy_mode=autonomy_mode,
                created_at=_now(),
                created_by=requested_by,
                target_id=target_id,
            )

        # Compute and store risk
        risk_data = await self.risk.score_case(case_id)
        risk_id = await self._create_risk_assessment(case_id, risk_data)

        # Update severity from risk score
        await self._update_case(case_id, {"severity": risk_data.get("severity", "medium")})

        await events.emit_case_created(case_id, title)
        return case_id

    async def run_resolution(self, case_id: str, requesting_user: str) -> None:
        """Background task: generate plan, evaluate actions, update case status."""
        try:
            plan_id = await self.planner.build_plan(case_id, requesting_user)

            # Count actions
            action_count = await self._count_actions(plan_id)
            await events.emit_plan_generated(case_id, plan_id, action_count)

            # Emit per-action events
            actions = await self._get_plan_actions(plan_id)
            for action in actions:
                action_id = action["action_id"]
                action_type = action["action_type"]
                status = action["status"]
                if status == "allowed":
                    await events.emit_action_allowed(case_id, action_id, action_type)
                elif status == "blocked":
                    await events.emit_action_blocked(case_id, action_id, action_type, action.get("reason", ""))
                elif status == "queued_for_review":
                    await events.emit_review_requested(case_id, action_id, action_type)

            # Update case status
            has_review = any(a["status"] == "queued_for_review" for a in actions)
            new_status = "awaiting_review" if has_review else "resolved"
            await self._update_case(case_id, {"status": new_status})

        except Exception as e:
            await self._update_case(case_id, {"status": "failed", "error": str(e)})

    async def get_case(self, case_id: str) -> Optional[dict[str, Any]]:
        """Fetch full case detail with risk, plan, actions, and related nodes."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})
                OPTIONAL MATCH (rc)-[:HAS_RISK]->(ra:RiskAssessment)
                OPTIONAL MATCH (rc)-[:HAS_PLAN]->(rp:ResolutionPlan)
                OPTIONAL MATCH (rp)-[:PROPOSES]->(pa:ProposedAction)
                OPTIONAL MATCH (rc)-[:ABOUT]->(related)
                RETURN rc, ra, rp,
                    collect(DISTINCT pa) AS actions,
                    collect(DISTINCT {id: related.id, label: labels(related)[0]}) AS related_nodes
                LIMIT 1
                """,
                case_id=case_id,
            )
            row = await result.single()

        if not row:
            return None

        rc = dict(row["rc"])
        ra = dict(row["ra"]) if row["ra"] else None
        rp = dict(row["rp"]) if row["rp"] else None
        actions = [dict(a) for a in (row["actions"] or []) if a]
        related_raw = [r for r in (row["related_nodes"] or []) if r.get("id")]

        related_nodes = {
            "decisions": [r["id"] for r in related_raw if r.get("label") == "Decision"],
            "approvals": [r["id"] for r in related_raw if r.get("label") == "Approval"],
            "tasks": [r["id"] for r in related_raw if r.get("label") == "Task"],
        }

        return {
            "case": rc,
            "risk_assessment": ra,
            "plan": rp,
            "actions": actions,
            "related_nodes": related_nodes,
        }

    async def list_cases(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List resolution cases with optional filters."""
        filters = []
        params: dict[str, Any] = {"limit": limit}

        if status:
            filters.append("rc.status = $status")
            params["status"] = status
        if severity:
            filters.append("rc.severity = $severity")
            params["severity"] = severity
        if case_type:
            filters.append("rc.case_type = $case_type")
            params["case_type"] = case_type

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (rc:ResolutionCase)
                {where_clause}
                RETURN rc
                ORDER BY rc.created_at DESC
                LIMIT $limit
                """,
                **params,
            )
            data = await result.data()

        return [dict(r["rc"]) for r in data]

    async def review_action(
        self,
        case_id: str,
        action_id: str,
        reviewed_by: str,
        decision: str,
        comment: Optional[str] = None,
    ) -> None:
        """Record a human review decision on a proposed action."""
        review_id = _new_id("RD")
        new_action_status = "allowed" if decision == "approved" else "cancelled"

        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (pa:ProposedAction {id: $action_id})
                CREATE (rd:ReviewDecision {
                    id: $review_id,
                    decision: $decision,
                    reviewed_by: $reviewed_by,
                    reviewed_at: $reviewed_at,
                    comment: $comment
                })
                CREATE (pa)-[:REVIEWED_AS]->(rd)
                SET pa.status = $new_status
                """,
                action_id=action_id,
                review_id=review_id,
                decision=decision,
                reviewed_by=reviewed_by,
                reviewed_at=_now(),
                comment=comment or "",
                new_status=new_action_status,
            )

        # Check if case can advance
        await self._check_and_advance_case(case_id)

    async def execute_reviewed_action(self, case_id: str, action_id: str) -> None:
        """Execute an action that has been approved via review."""
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (pa:ProposedAction {id: $action_id}) RETURN pa",
                action_id=action_id,
            )
            row = await result.single()

        if not row:
            return

        action = dict(row["pa"])
        if action.get("status") != "allowed":
            return

        agent_action_id = _new_id("AA")
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (pa:ProposedAction {id: $action_id})
                SET pa.status = 'executed', pa.executed_at = $executed_at
                WITH pa
                CREATE (aa:AgentAction {
                    id: $agent_action_id,
                    action_type: pa.action_type,
                    initiated_by: 'system',
                    executed_by_agent: 'digiTwin',
                    policy_path: pa.policy_path,
                    status: 'executed',
                    timestamp: $executed_at
                })
                CREATE (aa)-[:EXECUTES]->(pa)
                """,
                action_id=action_id,
                executed_at=_now(),
                agent_action_id=agent_action_id,
            )

        await events.emit_action_executed(case_id, action_id, action.get("action_type", "unknown"))
        await self._check_and_advance_case(case_id)

    async def stop_case(self, case_id: str) -> None:
        """Cancel a resolution case."""
        await self._update_case(case_id, {"status": "cancelled"})

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _derive_case_metadata(self, target_type: str, target_id: str) -> tuple[str, str]:
        """Look up the target node to get a human-readable title and case type."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (n {id: $target_id})
                RETURN coalesce(n.title, n.text, n.name, $target_id) AS title,
                       labels(n)[0] AS label
                LIMIT 1
                """,
                target_id=target_id,
            )
            row = await result.single()

        if not row:
            return f"Resolution for {target_type} {target_id}", "dependency_cluster"

        label = row["label"] or target_type
        title = row["title"] or target_id

        case_type_map = {
            "Decision": "launch_blocker",
            "Approval": "stale_approval",
            "Assumption": "contradiction",
            "Task": "dependency_cluster",
            "Project": "launch_blocker",
        }
        case_type = case_type_map.get(label, "dependency_cluster")
        return f"Resolve: {title}", case_type

    async def _create_risk_assessment(self, case_id: str, risk_data: dict) -> str:
        """Persist a RiskAssessment node linked to the case."""
        risk_id = _new_id("RA")
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})
                CREATE (ra:RiskAssessment {
                    id: $risk_id,
                    risk_score: $risk_score,
                    blast_radius_score: $blast_radius_score,
                    staleness_score: $staleness_score,
                    contradiction_score: $contradiction_score,
                    dependency_score: $dependency_score,
                    notes: $notes,
                    created_at: $created_at
                })
                CREATE (rc)-[:HAS_RISK]->(ra)
                """,
                case_id=case_id,
                risk_id=risk_id,
                risk_score=risk_data.get("risk_score", 0),
                blast_radius_score=risk_data.get("blast_radius_score", 0),
                staleness_score=risk_data.get("staleness_score", 0),
                contradiction_score=risk_data.get("contradiction_score", 0),
                dependency_score=risk_data.get("dependency_score", 0),
                notes=risk_data.get("notes", ""),
                created_at=_now(),
            )
        return risk_id

    async def _update_case(self, case_id: str, props: dict) -> None:
        set_parts = ", ".join(f"rc.{k} = ${k}" for k in props)
        async with self.driver.session() as session:
            await session.run(
                f"MATCH (rc:ResolutionCase {{id: $case_id}}) SET {set_parts}",
                case_id=case_id,
                **props,
            )

    async def _count_actions(self, plan_id: str) -> int:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (rp:ResolutionPlan {id: $plan_id})-[:PROPOSES]->(pa) RETURN count(pa) AS cnt",
                plan_id=plan_id,
            )
            row = await result.single()
        return row["cnt"] if row else 0

    async def _get_plan_actions(self, plan_id: str) -> list[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (rp:ResolutionPlan {id: $plan_id})-[:PROPOSES]->(pa) RETURN pa",
                plan_id=plan_id,
            )
            data = await result.data()
        return [dict(r["pa"]) for r in data]

    async def _check_and_advance_case(self, case_id: str) -> None:
        """Check if all actions are done and auto-resolve the case."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})-[:HAS_PLAN]->(rp)-[:PROPOSES]->(pa)
                RETURN
                    count(pa) AS total,
                    count(CASE WHEN pa.status IN ['executed', 'cancelled', 'blocked'] THEN 1 END) AS done,
                    count(CASE WHEN pa.status = 'queued_for_review' THEN 1 END) AS pending_review
                """,
                case_id=case_id,
            )
            row = await result.single()

        if not row or row["total"] == 0:
            return

        if row["pending_review"] > 0:
            await self._update_case(case_id, {"status": "awaiting_review"})
        elif row["done"] == row["total"]:
            await self._update_case(case_id, {"status": "resolved"})
            await events.emit_case_resolved(case_id)
