"""Heuristic risk scoring for resolution cases and proposed actions."""

from datetime import datetime, timezone

from neo4j import AsyncDriver


# Action type → risk level mapping (MVP allowlist items are all low-risk)
ACTION_RISK_MAP: dict[str, str] = {
    "send_reminder": "low",
    "request_update": "low",
    "notify_owner": "low",
    "prepare_review_packet": "low",
    "schedule_followup_check": "low",
    "draft_escalation": "medium",
    "escalate_to_exec": "high",
}

# MVP auto-execute allowlist
AUTO_EXECUTE_ALLOWLIST = frozenset([
    "send_reminder",
    "notify_owner",
    "request_update",
    "prepare_review_packet",
    "schedule_followup_check",
])


class RiskService:
    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    async def score_case(self, case_id: str) -> dict:
        """Compute heuristic risk scores for a resolution case.

        Returns a dict matching RiskAssessment node properties.
        """
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (rc:ResolutionCase {id: $case_id})-[:ABOUT]->(target)
                OPTIONAL MATCH (a:Assumption)-[:DEPENDS_ON]->(target)
                WHERE a.status = 'contradicted'
                OPTIONAL MATCH (ap:Approval)-[:FOR_DECISION]->(target)
                WHERE ap.status = 'pending'
                OPTIONAL MATCH (blocker)-[:BLOCKS]->(target)
                OPTIONAL MATCH (target)<-[:DEPENDS_ON*1..3]-(downstream)
                RETURN
                    count(DISTINCT a)        AS contradiction_count,
                    count(DISTINCT ap)       AS pending_approval_count,
                    count(DISTINCT blocker)  AS blocker_count,
                    count(DISTINCT downstream) AS downstream_count,
                    collect(DISTINCT ap.due_date)[0] AS oldest_due_date,
                    target.status           AS target_status
                """,
                case_id=case_id,
            )
            row = await result.single()

        if not row:
            return _zero_risk()

        contradiction_count = row["contradiction_count"] or 0
        pending_approval_count = row["pending_approval_count"] or 0
        blocker_count = row["blocker_count"] or 0
        downstream_count = row["downstream_count"] or 0
        target_status = row["target_status"] or ""
        oldest_due_date = row["oldest_due_date"]

        # Staleness bonus: how overdue is the oldest approval?
        stale_bonus = 0
        if oldest_due_date:
            try:
                due = datetime.fromisoformat(oldest_due_date.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                overdue_days = (now - due).days
                stale_bonus = max(0, min(overdue_days, 10))  # cap at 10
            except Exception:
                pass

        # Critical project bonus
        critical_bonus = 3 if target_status in ("approved", "proposed") else 0

        # Component scores
        contradiction_score = contradiction_count * 3
        staleness_score = stale_bonus
        dependency_score = downstream_count * 2
        blast_radius_score = blocker_count * 2 + downstream_count

        risk_score = (
            contradiction_score
            + pending_approval_count * 2
            + staleness_score
            + blast_radius_score
            + critical_bonus
        )

        severity = _severity_from_score(risk_score)

        return {
            "risk_score": risk_score,
            "blast_radius_score": blast_radius_score,
            "staleness_score": staleness_score,
            "contradiction_score": contradiction_score,
            "dependency_score": dependency_score,
            "notes": f"Heuristic: {contradiction_count} contradictions, {pending_approval_count} pending approvals, {blocker_count} blockers",
            "severity": severity,
        }

    def score_action(self, action_type: str) -> str:
        """Return risk level string for a given action type."""
        return ACTION_RISK_MAP.get(action_type, "medium")

    def is_auto_executable(self, action_type: str, risk_level: str) -> bool:
        """Check if an action can be auto-executed under auto_low_risk mode."""
        return action_type in AUTO_EXECUTE_ALLOWLIST and risk_level == "low"


def _zero_risk() -> dict:
    return {
        "risk_score": 0,
        "blast_radius_score": 0,
        "staleness_score": 0,
        "contradiction_score": 0,
        "dependency_score": 0,
        "notes": "No context found",
        "severity": "low",
    }


def _severity_from_score(score: int) -> str:
    if score >= 20:
        return "critical"
    if score >= 12:
        return "high"
    if score >= 5:
        return "medium"
    return "low"
