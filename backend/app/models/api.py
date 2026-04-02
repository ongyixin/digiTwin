from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

from app.models.graph import GraphSubgraph


class IngestResponse(BaseModel):
    meeting_id: str
    entities_created: dict[str, int]
    decision_ids: list[str]
    assumption_ids: list[str]


class QueryRequest(BaseModel):
    question: str
    user_id: str = "anonymous"
    top_k: int = 5


class Citation(BaseModel):
    id: str
    label: str
    title: str
    excerpt: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    policy_path: Optional[str] = None
    graph_context: Optional[list[dict[str, Any]]] = None


class PermissionCheckRequest(BaseModel):
    user_id: str
    action: str
    resource_id: str


class PermissionCheckResponse(BaseModel):
    allowed: bool
    policy_path: list[str]
    requires_approval: bool = False
    approver: Optional[str] = None
    reason: Optional[str] = None


class AgentActionResponse(BaseModel):
    id: str
    action_type: str
    initiated_by: str
    executed_by_agent: str = "digiTwin"
    policy_path: list[str] = []
    status: str = "allowed"
    timestamp: str


class DraftFollowupRequest(BaseModel):
    user_id: str
    decision_id: Optional[str] = None


class DraftedMessage(BaseModel):
    target_person_id: str
    target_person_name: str
    subject: str
    body: str
    policy_path: list[str]
    blocked: bool = False
    block_reason: Optional[str] = None


class DraftFollowupResponse(BaseModel):
    drafted: list[DraftedMessage]
    blocked_count: int
    agent_action_id: str


# ---------------------------------------------------------------------------
# Job / pipeline observability models
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class StageStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class StageInfo(BaseModel):
    name: str
    status: StageStatus = StageStatus.pending
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    entities_found: int = 0
    detail: Optional[str] = None


class TwinDiffItem(BaseModel):
    id: str
    title: str
    label: str
    href: Optional[str] = None


class TwinDiff(BaseModel):
    new_decisions: list[TwinDiffItem] = []
    new_assumptions: list[TwinDiffItem] = []
    superseded_assumptions: list[TwinDiffItem] = []
    new_evidence: list[TwinDiffItem] = []
    new_tasks: list[TwinDiffItem] = []
    new_approvals: list[TwinDiffItem] = []


class JobState(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.queued
    # Generalized fields
    artifact_title: str = ""
    artifact_type: str = "transcript"
    artifact_id: Optional[str] = None
    # Legacy field kept for backward compatibility
    meeting_title: str = ""
    created_at: str
    completed_at: Optional[str] = None
    stages: list[StageInfo] = []
    entities_created: dict[str, int] = {}
    error: Optional[str] = None
    twin_diff: Optional[TwinDiff] = None
    meeting_id: Optional[str] = None


class IngestJobResponse(BaseModel):
    """Returned immediately from any async ingest endpoint."""
    job_id: str
    status: JobStatus = JobStatus.queued
    artifact_type: str = "transcript"


# ---------------------------------------------------------------------------
# Review Inbox models
# ---------------------------------------------------------------------------


class ReviewTask(BaseModel):
    id: str
    action_type: str
    initiated_by: str
    reason: str
    original_action_id: str
    created_at: str
    status: str = "pending"


class ReviewDecision(BaseModel):
    approved: bool
    reviewer_id: str
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Impact / blast radius models
# ---------------------------------------------------------------------------


class ImpactScore(BaseModel):
    decision_id: str
    impact_score: float
    blast_radius: int
    downstream_decisions: int
    blocked_tasks: int
    pending_approvals: int
    central_approvers: list[str] = []


# ---------------------------------------------------------------------------
# Policy Sandbox models
# ---------------------------------------------------------------------------


class HypotheticalGrant(BaseModel):
    user_id: str
    role: str
    resource_id: Optional[str] = None


class HypotheticalDelegation(BaseModel):
    from_user_id: str
    to_user_id: str


class PolicySimulateRequest(BaseModel):
    user_id: str
    action: str
    resource_id: str
    hypothetical_grants: list[HypotheticalGrant] = []
    hypothetical_delegations: list[HypotheticalDelegation] = []


class PolicySimulateResponse(BaseModel):
    original: "PermissionCheckResponse"
    simulated: "PermissionCheckResponse"
    policy_path_diff: list[str] = []
