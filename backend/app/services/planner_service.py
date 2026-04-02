"""LLM-driven resolution plan generation."""

import json
import os
from datetime import datetime, timezone
from typing import Any

from neo4j import AsyncDriver

from app.llm.base import GenerateConfig, LLMProvider
from app.services.graph_service import GraphService, _new_id
from app.services.permission_service import PermissionService
from app.services.risk_service import RiskService


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "generate_resolution_plan.txt")
    with open(prompt_path) as f:
        return f.read()


class PlannerService:
    def __init__(self, driver: AsyncDriver, llm: LLMProvider):
        self.driver = driver
        self.llm = llm
        self.graph = GraphService(driver)
        self.permissions = PermissionService(driver)
        self.risk = RiskService(driver)

    async def build_plan(self, case_id: str, requesting_user: str) -> str:
        """Generate a ResolutionPlan for a case. Returns the plan_id."""
        context = await self._gather_context(case_id)
        if not context:
            return await self._create_empty_plan(case_id)

        actions_raw = await self._generate_candidate_actions(context)
        plan_summary = actions_raw.get("summary", "Resolution plan generated.")
        candidate_actions = actions_raw.get("actions", [])

        plan_id = _new_id("RP")
        plan_risk = context.get("risk_score", 0)

        # Persist the plan node
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})
                CREATE (rp:ResolutionPlan {
                    id: $plan_id,
                    summary: $summary,
                    risk_score: $risk_score,
                    confidence_score: $confidence_score,
                    execution_mode: $execution_mode,
                    generated_at: $generated_at,
                    model_name: $model_name
                })
                CREATE (rc)-[:HAS_PLAN]->(rp)
                """,
                case_id=case_id,
                plan_id=plan_id,
                summary=plan_summary,
                risk_score=plan_risk,
                confidence_score=0.75,
                execution_mode=context.get("autonomy_mode", "recommend"),
                generated_at=_now(),
                model_name="gemini-2.5-flash",
            )

        # Create ProposedAction nodes for each candidate
        for raw_action in candidate_actions:
            await self._create_proposed_action(
                plan_id=plan_id,
                case_id=case_id,
                raw_action=raw_action,
                requesting_user=requesting_user,
                autonomy_mode=context.get("autonomy_mode", "recommend"),
            )

        return plan_id

    async def _gather_context(self, case_id: str) -> dict[str, Any]:
        """Fetch the 2-hop neighborhood around the ABOUT target."""
        async with self.driver.session() as session:
            # Get case + target
            result = await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})-[:ABOUT]->(target)
                RETURN rc, target, labels(target)[0] AS target_label
                LIMIT 1
                """,
                case_id=case_id,
            )
            row = await result.single()
            if not row:
                return {}

            rc = dict(row["rc"])
            target = dict(row["target"])
            target_label = row["target_label"]

            # Get blockers
            result2 = await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})-[:ABOUT]->(target)
                OPTIONAL MATCH (blocker)-[:BLOCKS]->(target)
                RETURN collect(DISTINCT {id: blocker.id, type: labels(blocker)[0], text: coalesce(blocker.title, blocker.text, blocker.id)}) AS blockers
                """,
                case_id=case_id,
            )
            row2 = await result2.single()
            blockers = [b for b in (row2["blockers"] if row2 else []) if b.get("id")]

            # Get pending approvals
            result3 = await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})-[:ABOUT]->(target)
                OPTIONAL MATCH (ap:Approval {status: 'pending'})-[:FOR_DECISION]->(target)
                OPTIONAL MATCH (p:Person)-[:ASSIGNED_TO]->(ap)
                RETURN collect(DISTINCT {id: ap.id, required_by: ap.required_by, due_date: ap.due_date, assignee: p.name}) AS approvals
                """,
                case_id=case_id,
            )
            row3 = await result3.single()
            approvals = [a for a in (row3["approvals"] if row3 else []) if a.get("id")]

            # Get contradicted assumptions
            result4 = await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})-[:ABOUT]->(target)
                OPTIONAL MATCH (a:Assumption {status: 'contradicted'})-[:DEPENDS_ON]->(target)
                RETURN collect(DISTINCT {id: a.id, text: a.text}) AS contradictions
                """,
                case_id=case_id,
            )
            row4 = await result4.single()
            contradictions = [c for c in (row4["contradictions"] if row4 else []) if c.get("id")]

            # Get downstream count
            result5 = await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})-[:ABOUT]->(target)
                OPTIONAL MATCH (target)<-[:DEPENDS_ON*1..3]-(downstream)
                RETURN count(DISTINCT downstream) AS downstream_count
                """,
                case_id=case_id,
            )
            row5 = await result5.single()
            downstream_count = row5["downstream_count"] if row5 else 0

        return {
            "case_id": case_id,
            "case_title": rc.get("title", "Unknown"),
            "case_type": rc.get("case_type", "unknown"),
            "severity": rc.get("severity", "medium"),
            "autonomy_mode": rc.get("autonomy_mode", "recommend"),
            "risk_score": rc.get("risk_score", 0),
            "target": target,
            "target_label": target_label,
            "blockers": blockers,
            "approvals": approvals,
            "contradictions": contradictions,
            "downstream_count": downstream_count,
        }

    async def _generate_candidate_actions(self, context: dict[str, Any]) -> dict[str, Any]:
        """Call LLM with the graph context to generate candidate actions."""
        target = context.get("target", {})
        target_summary = (
            f"ID: {target.get('id', 'unknown')}, "
            f"Type: {context.get('target_label', 'unknown')}, "
            f"Title: {target.get('title', target.get('text', 'unknown'))}"
        )

        blockers = context.get("blockers", [])
        blockers_summary = "\n".join(
            f"- [{b.get('type', '?')}] {b.get('id', '?')}: {b.get('text', '(no text)')}"
            for b in blockers
        ) or "None"

        approvals = context.get("approvals", [])
        approvals_summary = "\n".join(
            f"- [Approval] {a.get('id', '?')}: required by {a.get('required_by', '?')}, due {a.get('due_date', 'unknown')}, assignee: {a.get('assignee', 'unassigned')}"
            for a in approvals
        ) or "None"

        contradictions = context.get("contradictions", [])
        contradictions_summary = "\n".join(
            f"- [Assumption] {c.get('id', '?')}: {c.get('text', '(no text)')}"
            for c in contradictions
        ) or "None"

        prompt = _load_prompt().format(
            case_id=context["case_id"],
            case_title=context["case_title"],
            case_type=context["case_type"],
            severity=context["severity"],
            autonomy_mode=context["autonomy_mode"],
            target_summary=target_summary,
            blocker_count=len(blockers),
            blockers_summary=blockers_summary,
            pending_approval_count=len(approvals),
            approvals_summary=approvals_summary,
            contradiction_count=len(contradictions),
            contradictions_summary=contradictions_summary,
            downstream_count=context.get("downstream_count", 0),
        )

        raw = await self.llm.generate(
            prompt,
            GenerateConfig(temperature=0.3, response_mime_type="application/json"),
        )

        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {"summary": "Plan generated.", "actions": []}

    async def _create_proposed_action(
        self,
        plan_id: str,
        case_id: str,
        raw_action: dict[str, Any],
        requesting_user: str,
        autonomy_mode: str,
    ) -> str:
        """Persist a ProposedAction node after permission evaluation."""
        action_type = raw_action.get("action_type", "request_update")
        target_type = raw_action.get("target_type", "unknown")
        target_id = raw_action.get("target_id", "unknown")
        reason = raw_action.get("reason", "")
        evidence_refs = raw_action.get("evidence_refs", [])

        risk_level = self.risk.score_action(action_type)

        # Permission check: map action_type to permission action
        perm_action = action_type.replace("_", "-")
        resource_id = target_id if target_id and target_id != "unknown" else "global"

        perm_result = await self.permissions.check_permission(requesting_user, perm_action, resource_id)

        if perm_result.allowed:
            status = "allowed"
            requires_review = False
        elif perm_result.requires_approval:
            status = "queued_for_review"
            requires_review = True
        else:
            status = "blocked"
            requires_review = False

        action_id = _new_id("PA")
        policy_path = perm_result.policy_path

        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (rp:ResolutionPlan {id: $plan_id})
                CREATE (pa:ProposedAction {
                    id: $action_id,
                    action_type: $action_type,
                    target_type: $target_type,
                    target_id: $target_id,
                    status: $status,
                    risk_level: $risk_level,
                    requires_review: $requires_review,
                    reason: $reason,
                    policy_path: $policy_path,
                    evidence_refs: $evidence_refs,
                    created_at: $created_at
                })
                CREATE (rp)-[:PROPOSES]->(pa)
                """,
                plan_id=plan_id,
                action_id=action_id,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                status=status,
                risk_level=risk_level,
                requires_review=requires_review,
                reason=reason,
                policy_path=policy_path,
                evidence_refs=evidence_refs,
                created_at=_now(),
            )

            # Link to target if it exists
            if target_id and target_id != "unknown":
                await session.run(
                    """
                    MATCH (pa:ProposedAction {id: $action_id})
                    OPTIONAL MATCH (target {id: $target_id})
                    FOREACH (_ IN CASE WHEN target IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (pa)-[:TARGETS]->(target)
                    )
                    """,
                    action_id=action_id,
                    target_id=target_id,
                )

        return action_id

    async def _create_empty_plan(self, case_id: str) -> str:
        """Create a minimal plan when no context is available."""
        plan_id = _new_id("RP")
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})
                CREATE (rp:ResolutionPlan {
                    id: $plan_id,
                    summary: 'No graph context found. Manual investigation required.',
                    risk_score: 0,
                    confidence_score: 0.0,
                    execution_mode: 'recommend',
                    generated_at: $generated_at,
                    model_name: 'none'
                })
                CREATE (rc)-[:HAS_PLAN]->(rp)
                """,
                case_id=case_id,
                plan_id=plan_id,
                generated_at=_now(),
            )
        return plan_id
