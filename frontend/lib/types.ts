export interface Decision {
  id: string;
  title: string;
  summary: string;
  status: "proposed" | "approved" | "superseded" | "rejected";
  confidence: number;
  created_at: string;
  owner_name?: string;
  meeting_title?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface GraphSubgraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Citation {
  id: string;
  label: string;
  title: string;
  excerpt?: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  policy_path?: string;
  graph_context?: Record<string, unknown>[];
}

export interface PermissionCheckResponse {
  allowed: boolean;
  policy_path: string[];
  requires_approval: boolean;
  approver?: string;
  reason?: string;
}

export interface DraftedMessage {
  target_person_id: string;
  target_person_name: string;
  subject: string;
  body: string;
  policy_path: string[];
  blocked: boolean;
  block_reason?: string;
}

export interface DraftFollowupResponse {
  drafted: DraftedMessage[];
  blocked_count: number;
  agent_action_id: string;
}

export interface IngestResponse {
  meeting_id: string;
  entities_created: Record<string, number>;
  decision_ids: string[];
  assumption_ids: string[];
}

export interface AgentAction {
  id: string;
  action_type: string;
  initiated_by: string;
  executed_by_agent: string;
  policy_path: string[];
  status: string;
  timestamp: string;
}

export interface Assumption {
  id: string;
  text: string;
  status: "active" | "validated" | "contradicted";
  risk_level: string;
  decision_id?: string;
}

export interface Approval {
  id: string;
  status: "pending" | "approved" | "rejected";
  required_by?: string;
  due_date?: string;
  decision_id?: string;
  assigned_to_id?: string;
}

// ---------------------------------------------------------------------------
// Job / Pipeline observability types
// ---------------------------------------------------------------------------

export type JobStatus = "queued" | "running" | "completed" | "failed";
export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface StageInfo {
  name: string;
  status: StageStatus;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  entities_found: number;
  detail?: string;
}

export interface TwinDiffItem {
  id: string;
  title: string;
  label: string;
  href?: string;
}

export interface TwinDiff {
  new_decisions: TwinDiffItem[];
  new_assumptions: TwinDiffItem[];
  superseded_assumptions: TwinDiffItem[];
  new_evidence: TwinDiffItem[];
  new_tasks: TwinDiffItem[];
  new_approvals: TwinDiffItem[];
}

export interface JobState {
  job_id: string;
  status: JobStatus;
  // Generalized artifact fields
  artifact_title: string;
  artifact_type: string;
  artifact_id?: string;
  // Legacy field kept for backward compat
  meeting_title: string;
  created_at: string;
  completed_at?: string;
  stages: StageInfo[];
  entities_created: Record<string, number>;
  error?: string;
  twin_diff?: TwinDiff;
  meeting_id?: string;
}

export interface IngestJobResponse {
  job_id: string;
  status: JobStatus;
  artifact_type?: string;
}

// ---------------------------------------------------------------------------
// Artifact types
// ---------------------------------------------------------------------------

export type ArtifactType =
  | "transcript"
  | "policy_doc"
  | "prd"
  | "rfc"
  | "postmortem"
  | "contract"
  | "audio"
  | "video"
  | "github_repo"
  | "generic_text";

export type SourceType = "upload" | "url" | "gcs" | "github" | "connector";
export type SensitivityLevel = "public" | "internal" | "confidential" | "restricted";

export interface ArtifactRecord {
  id: string;
  type: ArtifactType;
  title: string;
  source_type: SourceType;
  workspace_id: string;
  sensitivity: SensitivityLevel;
  status: string;
  ingested_at: string;
  version_count: number;
  archived?: boolean;
  archived_at?: string;
}

// ---------------------------------------------------------------------------
// Review Inbox types
// ---------------------------------------------------------------------------

export interface ReviewTask {
  id: string;
  action_type: string;
  initiated_by: string;
  reason: string;
  original_action_id: string;
  created_at: string;
  status: string;
}

// ---------------------------------------------------------------------------
// Autonomous Resolution Engine types
// ---------------------------------------------------------------------------

export type CaseType =
  | "launch_blocker"
  | "contradiction"
  | "stale_approval"
  | "dependency_cluster"
  | "policy_conflict";

export type CaseStatus =
  | "open"
  | "planning"
  | "executing"
  | "awaiting_review"
  | "monitoring"
  | "resolved"
  | "failed"
  | "cancelled";

export type ResolutionSeverity = "low" | "medium" | "high" | "critical";
export type AutonomyMode = "observe" | "recommend" | "auto_low_risk" | "escalate_only";
export type ResolutionActionType =
  | "send_reminder"
  | "draft_escalation"
  | "request_update"
  | "prepare_review_packet"
  | "notify_owner"
  | "schedule_followup_check";

export type ProposedActionStatus =
  | "proposed"
  | "allowed"
  | "blocked"
  | "executed"
  | "queued_for_review"
  | "failed"
  | "cancelled";

export type ActionRiskLevel = "low" | "medium" | "high";

export interface ResolutionCase {
  id: string;
  title: string;
  case_type: CaseType;
  status: CaseStatus;
  severity: ResolutionSeverity;
  autonomy_mode: AutonomyMode;
  created_at: string;
  created_by?: string;
  trigger_source?: string;
}

export interface ResolutionCaseListItem {
  case_id: string;
  title: string;
  case_type: CaseType;
  status: CaseStatus;
  severity: ResolutionSeverity;
  autonomy_mode: AutonomyMode;
  created_at: string;
}

export interface RiskAssessment {
  risk_score: number;
  blast_radius_score: number;
  staleness_score: number;
  contradiction_score: number;
  dependency_score: number;
  notes?: string;
}

export interface ResolutionPlan {
  id: string;
  summary: string;
  risk_score: number;
  confidence_score: number;
  generated_at: string;
  model_name?: string;
}

export interface ProposedAction {
  id: string;
  action_type: ResolutionActionType;
  status: ProposedActionStatus;
  risk_level: ActionRiskLevel;
  requires_review: boolean;
  target_type?: string;
  target_id?: string;
  reason?: string;
  policy_path: string[];
  evidence_refs: string[];
  executed_at?: string;
}

export interface ResolutionRelatedNodes {
  decisions: string[];
  approvals: string[];
  tasks: string[];
}

export interface ResolutionCaseDetail {
  case: ResolutionCase;
  risk_assessment?: RiskAssessment;
  plan?: ResolutionPlan;
  actions: ProposedAction[];
  related_nodes: ResolutionRelatedNodes;
}

export interface ResolutionStreamEvent {
  type:
    | "case_created"
    | "plan_generated"
    | "action_allowed"
    | "action_blocked"
    | "action_executed"
    | "review_requested"
    | "case_resolved"
    | "ping";
  case_id?: string;
  action_id?: string;
  action_type?: string;
  plan_id?: string;
  action_count?: number;
  reason?: string;
  ts?: string;
}

// ---------------------------------------------------------------------------
// Impact score types
// ---------------------------------------------------------------------------

export interface ImpactScore {
  decision_id: string;
  impact_score: number;
  blast_radius: number;
  downstream_decisions: number;
  blocked_tasks: number;
  pending_approvals: number;
  central_approvers: string[];
}
