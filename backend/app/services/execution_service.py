"""Permission-aware execution: draft follow-ups, enforce policy, log actions."""

from neo4j import AsyncDriver

from app.llm.base import GenerateConfig, LLMProvider
from app.models.api import DraftedMessage, DraftFollowupResponse
from app.services.graph_service import GraphService
from app.services.permission_service import PermissionService


DRAFT_PROMPT = """You are a professional assistant drafting a follow-up message on behalf of a product team.

Context:
- Decision: {decision_title}
- Pending approval required from: {person_name}
- Approval type: {required_by}

Draft a concise, professional follow-up reminder message. Include:
1. A clear subject line
2. Brief context about the decision
3. What approval is needed and why it's important
4. A specific call to action

Return JSON:
{{
  "subject": "...",
  "body": "..."
}}
"""


class ExecutionService:
    def __init__(self, driver: AsyncDriver, llm: LLMProvider):
        self.driver = driver
        self.llm = llm
        self.graph = GraphService(driver)
        self.permissions = PermissionService(driver)

    async def draft_followups(self, user_id: str, decision_id: str | None = None) -> DraftFollowupResponse:
        from app.services.graph_service import _new_id
        import json

        # Check if user can send reminders
        can_remind = await self.permissions.can_user_send_reminder(user_id)
        can_escalate = await self.permissions.can_user_escalate(user_id)

        # Get pending approvals
        pending = await self.graph.get_pending_approvals()
        if decision_id:
            pending = [p for p in pending if p.get("decision_id") == decision_id]

        drafted: list[DraftedMessage] = []
        policy_path_log: list[str] = []

        for approval in pending:
            person_id = approval.get("person_id", "")
            person_name = approval.get("person_name", "Unknown")
            decision_title = approval.get("decision_title", "Unknown Decision")
            required_by = approval.get("ap", {}).get("required_by", "approval")

            # Determine if this is an escalation or a reminder
            is_overdue = bool(approval.get("ap", {}).get("due_date"))
            is_escalation = is_overdue and not can_remind

            if is_escalation and not can_escalate:
                drafted.append(DraftedMessage(
                    target_person_id=person_id,
                    target_person_name=person_name,
                    subject="",
                    body="",
                    policy_path=[f"User:{user_id}", "Action:escalate", "Denied:no permission"],
                    blocked=True,
                    block_reason=f"You do not have permission to escalate approvals. "
                                 f"Only reminder messages are allowed.",
                ))
                continue

            if not can_remind:
                drafted.append(DraftedMessage(
                    target_person_id=person_id,
                    target_person_name=person_name,
                    subject="",
                    body="",
                    policy_path=[f"User:{user_id}", "Action:send-reminder", "Denied:no permission"],
                    blocked=True,
                    block_reason="You do not have permission to send reminders.",
                ))
                continue

            # Draft the message via LLM
            prompt = DRAFT_PROMPT.format(
                decision_title=decision_title,
                person_name=person_name,
                required_by=required_by or "sign-off",
            )
            raw = await self.llm.generate(
                prompt,
                GenerateConfig(temperature=0.4, response_mime_type="application/json"),
            )
            try:
                msg = json.loads(raw or "{}")
            except Exception:
                msg = {"subject": f"Action needed: {decision_title}", "body": "Please review and approve."}

            policy_path = [
                f"User:{user_id}",
                "Role:pm",
                "Permission:execute",
                "Resource:send-reminder",
                "Action:allowed",
            ]
            policy_path_log.extend(policy_path)

            drafted.append(DraftedMessage(
                target_person_id=person_id,
                target_person_name=person_name,
                subject=msg.get("subject", ""),
                body=msg.get("body", ""),
                policy_path=policy_path,
                blocked=False,
            ))

        # Log agent action
        blocked_count = sum(1 for d in drafted if d.blocked)
        action_status = "blocked" if blocked_count == len(drafted) and drafted else (
            "partial" if blocked_count > 0 else "allowed"
        )
        action_id = await self.graph.create_agent_action(
            action_type="draft_followups",
            initiated_by=user_id,
            policy_path=policy_path_log,
            status=action_status,
        )

        # Create ReviewTask nodes for blocked actions so they appear in the inbox
        if blocked_count > 0:
            for msg in drafted:
                if msg.blocked:
                    await self.graph.create_review_task(
                        original_action_id=action_id,
                        action_type="draft_followups",
                        initiated_by=user_id,
                        reason=msg.block_reason or "Action blocked by policy",
                    )

        return DraftFollowupResponse(
            drafted=drafted,
            blocked_count=blocked_count,
            agent_action_id=action_id,
        )
