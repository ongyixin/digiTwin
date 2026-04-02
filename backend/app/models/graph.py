from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DecisionStatus(str, Enum):
    proposed = "proposed"
    approved = "approved"
    superseded = "superseded"
    rejected = "rejected"


class AssumptionStatus(str, Enum):
    active = "active"
    validated = "validated"
    contradicted = "contradicted"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TaskStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"
    blocked = "blocked"


class Person(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    department: Optional[str] = None


class Team(BaseModel):
    id: str
    name: str


class Project(BaseModel):
    id: str
    name: str
    status: Optional[str] = None


class Decision(BaseModel):
    id: str
    title: str
    summary: str
    status: DecisionStatus = DecisionStatus.proposed
    confidence: float = 0.8
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_excerpt: Optional[str] = None
    owner_id: Optional[str] = None
    meeting_id: Optional[str] = None


class Assumption(BaseModel):
    id: str
    text: str
    status: AssumptionStatus = AssumptionStatus.active
    risk_level: str = "medium"
    decision_id: Optional[str] = None


class Evidence(BaseModel):
    id: str
    title: str
    content_summary: str
    source_type: str = "document"
    source_url: Optional[str] = None


class Task(BaseModel):
    id: str
    title: str
    status: TaskStatus = TaskStatus.open
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    decision_id: Optional[str] = None


class Approval(BaseModel):
    id: str
    status: ApprovalStatus = ApprovalStatus.pending
    required_by: Optional[str] = None
    due_date: Optional[datetime] = None
    decision_id: Optional[str] = None
    assigned_to_id: Optional[str] = None


class Meeting(BaseModel):
    id: str
    title: str
    date: datetime
    participants: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict[str, Any]


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphSubgraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
