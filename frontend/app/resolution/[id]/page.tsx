"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Crosshair,
  AlertTriangle,
  Clock,
  GitBranch,
  Shield,
  CheckCircle2,
  XCircle,
  Square,
  Zap,
  Eye,
  Lightbulb,
  ArrowUpRight,
  Activity,
} from "lucide-react";
import { useResolutionCase, useResolutionStream } from "@/lib/hooks";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { PolicyPathViewer } from "@/components/shared/PolicyPathViewer";
import { MetricCard } from "@/components/shared/MetricCard";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { CyclingGraphBackground } from "@/components/dashboard/GraphBackgrounds";
import { api } from "@/lib/api";
import type { ProposedAction, ResolutionStreamEvent } from "@/lib/types";

const AUTONOMY_ICONS: Record<string, React.ElementType> = {
  observe: Eye,
  recommend: Lightbulb,
  auto_low_risk: Zap,
  escalate_only: ArrowUpRight,
};

const ACTION_TYPE_LABELS: Record<string, string> = {
  send_reminder: "Send Reminder",
  draft_escalation: "Draft Escalation",
  request_update: "Request Update",
  prepare_review_packet: "Prepare Review Packet",
  notify_owner: "Notify Owner",
  schedule_followup_check: "Schedule Follow-up",
};

const RISK_COLORS: Record<string, string> = {
  low: "text-emerald-400",
  medium: "text-amber-400",
  high: "text-red-400",
};

function ActionRow({
  action,
  caseId,
  onReview,
}: {
  action: ProposedAction;
  caseId: string;
  onReview: () => void;
}) {
  const [loading, setLoading] = useState<"approve" | "reject" | "execute" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleReview(decision: "approved" | "rejected") {
    setLoading(decision === "approved" ? "approve" : "reject");
    setError(null);
    try {
      await api.reviewResolutionAction(caseId, action.id, {
        reviewed_by: "admin",
        decision,
      });
      onReview();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(null);
    }
  }

  async function handleExecute() {
    setLoading("execute");
    setError(null);
    try {
      await api.executeResolutionAction(caseId, action.id);
      onReview();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="bg-muted/20 border border-border rounded-lg p-3 space-y-2">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-foreground">
              {ACTION_TYPE_LABELS[action.action_type] ?? action.action_type}
            </span>
            <StatusBadge status={action.status} />
            <span className={`text-xs font-medium ${RISK_COLORS[action.risk_level] ?? "text-muted-foreground"}`}>
              {action.risk_level} risk
            </span>
          </div>
          {action.target_id && action.target_id !== "unknown" && (
            <div className="text-xs text-muted-foreground font-mono mt-0.5">
              → {action.target_type}: {action.target_id}
            </div>
          )}
          {action.reason && (
            <p className="text-xs text-muted-foreground mt-1">{action.reason}</p>
          )}
        </div>
        <div className="flex gap-1.5 shrink-0">
          {action.status === "queued_for_review" && (
            <>
              <button
                onClick={() => handleReview("approved")}
                disabled={!!loading}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-md hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
              >
                <CheckCircle2 className="w-3 h-3" />
                {loading === "approve" ? "…" : "Approve"}
              </button>
              <button
                onClick={() => handleReview("rejected")}
                disabled={!!loading}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-red-500/10 text-red-400 border border-red-500/30 rounded-md hover:bg-red-500/20 transition-colors disabled:opacity-50"
              >
                <XCircle className="w-3 h-3" />
                {loading === "reject" ? "…" : "Reject"}
              </button>
            </>
          )}
          {action.status === "allowed" && (
            <button
              onClick={handleExecute}
              disabled={!!loading}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded-md hover:bg-blue-500/20 transition-colors disabled:opacity-50"
            >
              <Zap className="w-3 h-3" />
              {loading === "execute" ? "…" : "Execute"}
            </button>
          )}
        </div>
      </div>
      {action.policy_path.length > 0 && (
        <PolicyPathViewer path={action.policy_path} compact />
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

function EventTimeline({ events }: { events: ResolutionStreamEvent[] }) {
  if (events.length === 0) return null;
  return (
    <div className="bg-card border border-border rounded-xl p-4 space-y-2">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold text-foreground">Live Events</span>
      </div>
      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        <AnimatePresence initial={false}>
          {events.slice().reverse().map((evt, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2 text-xs text-muted-foreground"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0" />
              <span className="font-mono text-muted-foreground/60">{evt.ts?.slice(11, 19)}</span>
              <span>{evt.type.replace(/_/g, " ")}</span>
              {evt.action_type && <span className="text-foreground/60">· {evt.action_type}</span>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function ResolutionCaseDetailPage() {
  const params = useParams();
  const caseId = params.id as string;
  const { data: detail, isLoading, refetch } = useResolutionCase(caseId);
  const { events } = useResolutionStream(caseId);
  const [stopping, setStopping] = useState(false);

  async function handleStop() {
    setStopping(true);
    try {
      await api.stopResolutionCase(caseId);
      refetch();
    } finally {
      setStopping(false);
    }
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <LoadingState rows={5} />
      </div>
    );
  }

  if (!detail) {
    return <div className="p-6 text-sm text-red-400">Resolution case not found.</div>;
  }

  const { case: rc, risk_assessment, plan, actions = [], related_nodes } = detail;
  const AutonomyIcon = AUTONOMY_ICONS[rc.autonomy_mode] ?? Crosshair;

  const executedActions = actions.filter((a) => a.status === "executed");
  const reviewActions = actions.filter((a) => a.status === "queued_for_review" || a.status === "allowed");
  const blockedActions = actions.filter((a) => a.status === "blocked" || a.status === "cancelled");

  return (
    <div className="relative">
      <CyclingGraphBackground opacity={0.2} />
      <div className="relative z-10 p-6 space-y-6 max-w-6xl mx-auto animate-fade-in">
        {/* Breadcrumb + header */}
        <div className="flex items-center gap-2 text-sm">
          <Link
            href="/resolution"
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Resolution Center
          </Link>
          <span className="text-muted-foreground/40">/</span>
          <span className="text-foreground font-medium truncate max-w-sm">{rc.title}</span>
        </div>

        {/* Case header card */}
        <div className="bg-card border border-border rounded-xl p-5 space-y-3">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={rc.status} />
              <SeverityBadge severity={rc.severity} />
              <div className="flex items-center gap-1 text-xs text-muted-foreground bg-muted/40 px-2 py-0.5 rounded-md">
                <AutonomyIcon className="w-3 h-3" />
                {rc.autonomy_mode}
              </div>
            </div>
            {!["resolved", "cancelled", "failed"].includes(rc.status) && (
              <button
                onClick={handleStop}
                disabled={stopping}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-muted text-muted-foreground border border-border rounded-md hover:border-red-500/40 hover:text-red-400 transition-colors disabled:opacity-50"
              >
                <Square className="w-3 h-3" />
                {stopping ? "Stopping…" : "Stop"}
              </button>
            )}
          </div>
          <h1 className="text-lg font-bold text-foreground">{rc.title}</h1>
          <div className="flex gap-4 text-xs text-muted-foreground font-mono">
            <span>{caseId}</span>
            {rc.created_by && <span>by {rc.created_by}</span>}
            {rc.created_at && <span>{new Date(rc.created_at).toLocaleString()}</span>}
          </div>
        </div>

        {/* Risk metrics */}
        {risk_assessment && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard label="Risk Score" value={risk_assessment.risk_score} icon={AlertTriangle} accent="crimson" size="sm" />
            <MetricCard label="Blast Radius" value={risk_assessment.blast_radius_score} icon={Activity} accent="amber" size="sm" />
            <MetricCard label="Staleness" value={risk_assessment.staleness_score} icon={Clock} accent="amber" size="sm" />
            <MetricCard label="Dependencies" value={risk_assessment.dependency_score} icon={GitBranch} accent="blue" size="sm" />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-4">
            {/* Plan summary */}
            {plan && (
              <div className="bg-card border border-border rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-primary" />
                  <span className="text-sm font-semibold text-foreground">Resolution Plan</span>
                  <span className="text-xs text-muted-foreground font-mono ml-auto">{plan.id}</span>
                </div>
                <p className="text-sm text-muted-foreground">{plan.summary}</p>
                <div className="text-xs text-muted-foreground font-mono">
                  confidence: {Math.round((plan.confidence_score ?? 0) * 100)}%
                  {plan.model_name && ` · ${plan.model_name}`}
                </div>
              </div>
            )}

            {/* No plan yet */}
            {!plan && rc.status === "planning" && (
              <div className="bg-card border border-border rounded-xl p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="w-3 h-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                  Generating resolution plan…
                </div>
              </div>
            )}

            {/* Actions sections */}
            {actions.length === 0 && !plan && rc.status !== "planning" && (
              <EmptyState title="No actions yet" description="The resolution plan is being generated." />
            )}

            {reviewActions.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wide flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  Awaiting Review ({reviewActions.length})
                </h3>
                {reviewActions.map((action) => (
                  <ActionRow key={action.id} action={action} caseId={caseId} onReview={() => refetch()} />
                ))}
              </div>
            )}

            {executedActions.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wide flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Executed ({executedActions.length})
                </h3>
                {executedActions.map((action) => (
                  <ActionRow key={action.id} action={action} caseId={caseId} onReview={() => refetch()} />
                ))}
              </div>
            )}

            {blockedActions.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-red-400 uppercase tracking-wide flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5" />
                  Blocked ({blockedActions.length})
                </h3>
                {blockedActions.map((action) => (
                  <ActionRow key={action.id} action={action} caseId={caseId} onReview={() => refetch()} />
                ))}
              </div>
            )}

            {/* Live events */}
            <EventTimeline events={events} />
          </div>

          {/* Right sidebar */}
          <div className="space-y-4">
            {/* Related nodes */}
            {related_nodes && (
              <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                <h3 className="text-sm font-semibold text-foreground">Related Entities</h3>
                {related_nodes.decisions.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1.5 flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                      Decisions
                    </div>
                    <div className="space-y-1">
                      {related_nodes.decisions.map((id) => (
                        <Link
                          key={id}
                          href={`/decisions/${id}`}
                          className="block text-xs text-muted-foreground hover:text-foreground font-mono transition-colors"
                        >
                          {id}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
                {related_nodes.approvals.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1.5 flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-red-400 shrink-0" />
                      Approvals
                    </div>
                    <div className="space-y-1">
                      {related_nodes.approvals.map((id) => (
                        <div key={id} className="text-xs text-muted-foreground font-mono">{id}</div>
                      ))}
                    </div>
                  </div>
                )}
                {related_nodes.tasks.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1.5 flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-violet-400 shrink-0" />
                      Tasks
                    </div>
                    <div className="space-y-1">
                      {related_nodes.tasks.map((id) => (
                        <div key={id} className="text-xs text-muted-foreground font-mono">{id}</div>
                      ))}
                    </div>
                  </div>
                )}
                {!related_nodes.decisions.length && !related_nodes.approvals.length && !related_nodes.tasks.length && (
                  <p className="text-xs text-muted-foreground">No related entities found.</p>
                )}
              </div>
            )}

            {/* Risk notes */}
            {risk_assessment?.notes && (
              <div className="bg-card border border-border rounded-xl p-4 space-y-1.5">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Risk Notes</h3>
                <p className="text-xs text-muted-foreground">{risk_assessment.notes}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
