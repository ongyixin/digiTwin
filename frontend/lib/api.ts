import type {
  ArtifactRecord,
  ArtifactType,
  Decision,
  GraphSubgraph,
  IngestJobResponse,
  IngestResponse,
  AgentAction,
  JobState,
  QueryResponse,
  PermissionCheckResponse,
  DraftFollowupResponse,
  ReviewTask,
  ImpactScore,
  ResolutionCaseListItem,
  ResolutionCaseDetail,
  AutonomyMode,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }
  return res.json();
}

export const api = {
  getDecisions: () => apiFetch<Decision[]>("/api/graph/decisions"),

  getDecisionLineage: (id: string) =>
    apiFetch<GraphSubgraph>(`/api/graph/decisions/${id}/lineage`),

  getGraphOverview: (workspace = "default") =>
    apiFetch<GraphSubgraph>(`/api/graph/overview?workspace=${workspace}`),

  query: (question: string, userId: string = "alex") =>
    apiFetch<QueryResponse>("/api/query", {
      method: "POST",
      body: JSON.stringify({ question, user_id: userId }),
    }),

  chatbot: (question: string, userId: string = "alex") =>
    apiFetch<QueryResponse>("/api/chatbot", {
      method: "POST",
      body: JSON.stringify({ question, user_id: userId }),
    }),

  checkPermission: (userId: string, action: string, resourceId: string) =>
    apiFetch<PermissionCheckResponse>("/api/permissions/check", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, action, resource_id: resourceId }),
    }),

  getUserPermissions: (userId: string) =>
    apiFetch<{ roles: string[]; permissions: { action: string; resource: string; scope?: string }[] }>(
      `/api/permissions/user/${userId}`
    ),

  draftFollowups: (userId: string, decisionId?: string) =>
    apiFetch<DraftFollowupResponse>("/api/actions/draft-followups", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, decision_id: decisionId }),
    }),

  getActionHistory: () => apiFetch<AgentAction[]>("/api/actions/history"),

  ingestText: (payload: {
    transcript: string;
    meeting_title: string;
    meeting_date: string;
    participants: string[];
  }) =>
    apiFetch<IngestJobResponse>("/api/ingest/text", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /** Canonical artifact ingest — multipart form upload */
  ingestArtifact: (formData: FormData) =>
    fetch(`${BASE_URL}/api/ingest/artifact`, {
      method: "POST",
      body: formData,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.text();
        throw new Error(`API error ${res.status}: ${err}`);
      }
      return res.json() as Promise<IngestJobResponse>;
    }),

  /** Ingest artifact by URL / GCS / GitHub reference (JSON body) */
  ingestArtifactUrl: (payload: {
    artifact_type: ArtifactType;
    source_type: string;
    source_url?: string;
    github_repo_url?: string;
    github_branch?: string;
    workspace_id?: string;
    sensitivity?: string;
    metadata?: Record<string, unknown>;
  }) =>
    apiFetch<IngestJobResponse>("/api/ingest/artifact/url", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getGitHubBranches: (repoUrl: string) =>
    apiFetch<{ branches: string[]; default_branch: string }>(
      `/api/ingest/github/branches?repo_url=${encodeURIComponent(repoUrl)}`
    ),

  listJobs: () => apiFetch<JobState[]>("/api/ingest/jobs"),

  getJob: (jobId: string) => apiFetch<JobState>(`/api/ingest/jobs/${jobId}`),

  listArtifacts: (workspaceId: string = "default", type?: ArtifactType) =>
    apiFetch<ArtifactRecord[]>(
      `/api/artifacts?workspace_id=${workspaceId}${type ? `&artifact_type=${type}` : ""}`
    ),

  listArchivedArtifacts: (workspaceId: string = "default", type?: ArtifactType) =>
    apiFetch<ArtifactRecord[]>(
      `/api/artifacts/archived?workspace_id=${workspaceId}${type ? `&artifact_type=${type}` : ""}`
    ),

  archiveArtifact: (id: string) =>
    apiFetch<{ success: boolean; artifact_id: string }>(`/api/artifacts/${id}/archive`, {
      method: "POST",
    }),

  unarchiveArtifact: (id: string) =>
    apiFetch<{ success: boolean; artifact_id: string }>(`/api/artifacts/${id}/unarchive`, {
      method: "POST",
    }),

  deleteArtifact: (id: string) =>
    apiFetch<{ success: boolean; artifact_id: string }>(`/api/artifacts/${id}`, {
      method: "DELETE",
    }),

  getDecisionImpact: (id: string) =>
    apiFetch<ImpactScore>(`/api/graph/decisions/${id}/impact`),

  getReviewInbox: () => apiFetch<ReviewTask[]>("/api/actions/review-inbox"),

  approveReview: (id: string, reviewerId: string, note?: string) =>
    apiFetch<{ success: boolean }>(`/api/actions/review/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved: true, reviewer_id: reviewerId, note }),
    }),

  rejectReview: (id: string, reviewerId: string, note?: string) =>
    apiFetch<{ success: boolean }>(`/api/actions/review/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved: false, reviewer_id: reviewerId, note }),
    }),

  getTimeline: () =>
    apiFetch<Decision[]>("/api/graph/timeline"),

  // ---------------------------------------------------------------------------
  // Resolution Engine
  // ---------------------------------------------------------------------------

  createResolutionCase: (payload: {
    target_type: string;
    target_id: string;
    requested_by: string;
    autonomy_mode: AutonomyMode;
  }) =>
    apiFetch<{ case_id: string; status: string }>("/api/resolution/resolve", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getResolutionCases: (params?: { status?: string; severity?: string; case_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.severity) qs.set("severity", params.severity);
    if (params?.case_type) qs.set("case_type", params.case_type);
    const q = qs.toString();
    return apiFetch<ResolutionCaseListItem[]>(`/api/resolution/cases${q ? `?${q}` : ""}`);
  },

  getResolutionCase: (caseId: string) =>
    apiFetch<ResolutionCaseDetail>(`/api/resolution/cases/${caseId}`),

  reviewResolutionAction: (
    caseId: string,
    actionId: string,
    payload: { reviewed_by: string; decision: "approved" | "rejected"; comment?: string }
  ) =>
    apiFetch<{ success: boolean }>(
      `/api/resolution/cases/${caseId}/actions/${actionId}/review`,
      { method: "POST", body: JSON.stringify(payload) }
    ),

  executeResolutionAction: (caseId: string, actionId: string) =>
    apiFetch<{ success: boolean }>(
      `/api/resolution/cases/${caseId}/actions/${actionId}/execute`,
      { method: "POST" }
    ),

  stopResolutionCase: (caseId: string) =>
    apiFetch<{ success: boolean }>(`/api/resolution/cases/${caseId}/stop`, { method: "POST" }),

  simulatePolicy: (payload: {
    user_id: string;
    action: string;
    resource_id: string;
    hypothetical_grants?: { user_id: string; role: string; resource_id?: string }[];
    hypothetical_delegations?: { from_user_id: string; to_user_id: string }[];
  }) =>
    apiFetch<{ original: PermissionCheckResponse; simulated: PermissionCheckResponse; policy_path_diff: string[] }>(
      "/api/permissions/simulate",
      { method: "POST", body: JSON.stringify(payload) }
    ),
};
