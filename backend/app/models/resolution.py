"""Pydantic models for the Autonomous Resolution Engine."""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CaseType(str, Enum):
    launch_blocker = "launch_blocker"
    contradiction = "contradiction"
    stale_approval = "stale_approval"
    dependency_cluster = "dependency_cluster"
    policy_conflict = "policy_conflict"


class CaseStatus(str, Enum):
    open = "open"
    planning = "planning"
    executing = "executing"
    awaiting_review = "awaiting_review"
    monitoring = "monitoring"
    resolved = "resolved"
    failed = "failed"
    cancelled = "cancelled"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AutonomyMode(str, Enum):
    observe = "observe"
    recommend = "recommend"
    auto_low_risk = "auto_low_risk"
    escalate_only = "escalate_only"


class ActionType(str, Enum):
    send_reminder = "send_reminder"
    draft_escalation = "draft_escalation"
    request_update = "request_update"
    prepare_review_packet = "prepare_review_packet"
    notify_owner = "notify_owner"
    schedule_followup_check = "schedule_followup_check"


class ActionStatus(str, Enum):
    proposed = "proposed"
    allowed = "allowed"
    blocked = "blocked"
    executed = "executed"
    queued_for_review = "queued_for_review"
    failed = "failed"
    cancelled = "cancelled"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateCaseRequest(BaseModel):
    target_type: str
    target_id: str
    requested_by: str
    autonomy_mode: AutonomyMode = AutonomyMode.recommend


class ReviewActionRequest(BaseModel):
    reviewed_by: str
    decision: Literal["approved", "rejected"]
    comment: Optional[str] = None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ResolutionCaseResponse(BaseModel):
    case_id: str
    status: str


class ResolutionCaseListItem(BaseModel):
    case_id: str
    title: str
    case_type: str
    status: str
    severity: str
    autonomy_mode: str
    created_at: str


class RiskAssessmentResponse(BaseModel):
    risk_score: int
    blast_radius_score: int
    staleness_score: int
    contradiction_score: int
    dependency_score: int
    notes: Optional[str] = None


class ResolutionPlanResponse(BaseModel):
    plan_id: str
    summary: str
    risk_score: int
    confidence_score: float
    generated_at: str
    model_name: Optional[str] = None


class ProposedActionResponse(BaseModel):
    action_id: str
    action_type: str
    status: str
    risk_level: str
    requires_review: bool
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    reason: Optional[str] = None
    policy_path: list[str] = []
    evidence_refs: list[str] = []
    executed_at: Optional[str] = None


class RelatedNodes(BaseModel):
    decisions: list[str] = []
    approvals: list[str] = []
    tasks: list[str] = []


class ResolutionCaseDetail(BaseModel):
    case: dict[str, Any]
    risk_assessment: Optional[dict[str, Any]] = None
    plan: Optional[dict[str, Any]] = None
    actions: list[dict[str, Any]] = []
    related_nodes: RelatedNodes = RelatedNodes()
