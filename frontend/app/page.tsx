"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  GitBranch, MessageSquare, Zap, Shield, Network, ScrollText,
  CheckCircle2, Clock, AlertTriangle, TrendingUp, Inbox, Database,
  Activity,
} from "lucide-react";
import { useDecisions, useActionHistory, useJobs } from "@/lib/hooks";
import { MetricCard } from "@/components/shared/MetricCard";
import { EntityCard } from "@/components/shared/EntityCard";
import { LoadingState } from "@/components/shared/LoadingState";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { OwnerChip } from "@/components/shared/OwnerChip";
import { PulseIndicator } from "@/components/shared/PulseIndicator";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ArtifactTypeBadge } from "@/components/shared/ArtifactTypeBadge";
import { ArtifactModal } from "@/components/shared/ArtifactModal";
import { MiniGraphPreview } from "@/components/dashboard/MiniGraphPreview";
import { ContextRail } from "@/components/dashboard/ContextRail";
import { HeroEmptyState } from "@/components/dashboard/HeroEmptyState";
import { CyclingGraphBackground } from "@/components/dashboard/GraphBackgrounds";
import { Button } from "@/components/ui/button";
import { PlusCircle } from "lucide-react";

const QUICK_NAV = [
  { label: "Decisions", href: "/decisions", icon: GitBranch, description: "Browse all extracted decisions", accent: "text-blue-400", bg: "bg-blue-500/10" },
  { label: "Artifacts", href: "/artifacts", icon: Database, description: "Ingested knowledge sources", accent: "text-violet-400", bg: "bg-violet-500/10" },
  { label: "Ask the Twin", href: "/ask", icon: MessageSquare, description: "Graph-grounded Q&A", accent: "text-emerald-400", bg: "bg-emerald-500/10" },
  { label: "Actions", href: "/actions", icon: Zap, description: "Draft policy-enforced follow-ups", accent: "text-amber-400", bg: "bg-amber-500/10" },
  { label: "Permissions", href: "/permissions", icon: Shield, description: "Inspect user roles & access", accent: "text-violet-400", bg: "bg-violet-500/10" },
  { label: "Dependency Map", href: "/dependency-map", icon: Network, description: "Visual knowledge graph", accent: "text-blue-400", bg: "bg-blue-500/10" },
  { label: "Audit", href: "/audit", icon: ScrollText, description: "Full action replay log", accent: "text-muted-foreground", bg: "bg-muted/60" },
  { label: "Review Inbox", href: "/review", icon: Inbox, description: "Approve or reject blocked actions", accent: "text-amber-400", bg: "bg-amber-500/10" },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  const { data: decisions, isLoading: decisionsLoading } = useDecisions();
  const { data: actions, isLoading: actionsLoading } = useActionHistory();
  const { data: jobs } = useJobs();

  const totalDecisions = decisions?.length ?? 0;
  const pendingApprovals = decisions?.filter((d) => d.status === "proposed").length ?? 0;
  const approvedDecisions = decisions?.filter((d) => d.status === "approved").length ?? 0;
  const blockedActions = actions?.filter((a) => a.status === "blocked" || a.status === "denied").length ?? 0;
  const hasRunning = jobs?.some((j) => j.status === "running");

  const avgConfidence =
    decisions && decisions.length > 0
      ? Math.round(
          (decisions.reduce((s, d) => s + (d.confidence ?? 0), 0) / decisions.length) * 100
        )
      : 0;

  const isEmpty = !decisionsLoading && !actionsLoading && totalDecisions === 0 && !actions?.length;

  if (isEmpty) {
    return (
      <div className="relative">
        <CyclingGraphBackground />
        <div className="relative z-10">
          <HeroEmptyState />
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <CyclingGraphBackground />

      <motion.div
        className="relative z-10 p-6 lg:p-10 space-y-10 max-w-[1400px] mx-auto"
        initial="hidden"
        animate="visible"
        variants={containerVariants}
      >
        {/* ── Hero Title Zone ──────────────────────────────────── */}
        <motion.div variants={itemVariants} className="pt-6 pb-2 space-y-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="space-y-2">
              <motion.div
                className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-full px-3 py-1"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse-dot" />
                <span className="text-xs font-medium text-primary">
                  {hasRunning ? "Syncing knowledge graph…" : "Twin active"}
                </span>
              </motion.div>
              <h1 className="text-4xl font-bold text-gradient-primary tracking-tight">
                Decision Intelligence
              </h1>
              <p className="text-base text-muted-foreground max-w-lg">
                Overview of your digital twin&rsquo;s knowledge state &mdash; decisions, actions, and policy enforcement at a glance.
              </p>
            </div>
            <ArtifactModal
              trigger={
                <Button size="lg" className="gap-2 shadow-glow">
                  <PlusCircle className="w-5 h-5" />
                  Add Artifact
                </Button>
              }
            />
          </div>
          <div className="gradient-rule" />
        </motion.div>

        {/* Main content + optional right rail */}
        <div className="flex gap-8">
          <div className="flex-1 min-w-0 space-y-10">

            {/* ── Metric Cards — bento grid ────────────────────── */}
            <motion.div variants={itemVariants}>
              {decisionsLoading ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className={`bg-card border border-border rounded-xl h-24 animate-shimmer ${i < 2 ? "col-span-2" : ""}`} />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {/* Twin Health — spans 2 cols */}
                  <div className="col-span-2">
                    <MetricCard
                      label="Twin Knowledge State"
                      value={totalDecisions}
                      icon={GitBranch}
                      accent="blue"
                      size="lg"
                      description={`${approvedDecisions} approved · ${avgConfidence}% avg confidence`}
                    />
                  </div>
                  <MetricCard
                    label="Pending Approval"
                    value={pendingApprovals}
                    icon={Clock}
                    accent="amber"
                    description={`${pendingApprovals} decision${pendingApprovals !== 1 ? "s" : ""} awaiting review`}
                  />
                  <MetricCard
                    label="Blocked Actions"
                    value={blockedActions}
                    icon={AlertTriangle}
                    accent="crimson"
                    description={blockedActions > 0 ? "Requires attention" : "All clear"}
                  />
                  {/* Row 2 */}
                  <MetricCard
                    label="Total Actions"
                    value={actions?.length ?? 0}
                    icon={TrendingUp}
                    accent="emerald"
                  />
                  <MetricCard
                    label="Approved"
                    value={approvedDecisions}
                    icon={CheckCircle2}
                    accent="emerald"
                  />
                  {/* System Pulse */}
                  <div className="col-span-2">
                    <div className="bg-card border border-border rounded-xl px-5 py-4 flex items-center gap-4">
                      <PulseIndicator color={hasRunning ? "primary" : "emerald"} pulse={hasRunning} size="md" />
                      <div>
                        <div className="text-base font-semibold text-foreground">
                          {hasRunning ? "Processing ingestion…" : "Twin active"}
                        </div>
                        <div className="text-sm text-muted-foreground mt-0.5">
                          {hasRunning ? "Graph update in progress" : "All systems nominal"}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>

            {/* ── Recent Decisions + Mini Graph ─────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Decisions */}
              <motion.div variants={itemVariants} className="space-y-4">
                <SectionHeader
                  title="Needs attention"
                  viewAllHref="/decisions"
                  count={decisions?.filter((d) => d.status === "proposed").length}
                />
                {decisionsLoading ? (
                  <LoadingState rows={3} />
                ) : decisions && decisions.length > 0 ? (
                  <div className="space-y-2.5">
                    {decisions.slice(0, 5).map((d) => (
                      <EntityCard
                        key={d.id}
                        id={d.id}
                        title={d.title}
                        summary={d.summary}
                        status={d.status}
                        confidence={d.confidence}
                        ownerName={d.owner_name}
                        meetingTitle={d.meeting_title}
                        href={`/decisions/${d.id}`}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="bg-card border border-border rounded-xl px-5 py-8 text-center text-base text-muted-foreground">
                    No decisions yet.{" "}
                    <ArtifactModal trigger={<button className="text-primary hover:underline font-medium">Add an artifact</button>} />{" "}
                    to get started.
                  </div>
                )}
              </motion.div>

              {/* Mini Graph */}
              <motion.div variants={itemVariants} className="space-y-4">
                <SectionHeader title="Knowledge graph" viewAllHref="/dependency-map" />
                <div className="bg-card border border-border rounded-xl p-5 relative overflow-hidden">
                  {/* Subtle graph-hint SVG in the card background */}
                  <svg className="absolute inset-0 w-full h-full opacity-[0.03] pointer-events-none" aria-hidden="true">
                    <pattern id="grid-dots" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
                      <circle cx="12" cy="12" r="1" fill="hsl(var(--foreground))" />
                    </pattern>
                    <rect width="100%" height="100%" fill="url(#grid-dots)" />
                  </svg>
                  <div className="relative">
                    {decisions && decisions.length > 0 ? (
                      <MiniGraphPreview decisions={decisions} />
                    ) : (
                      <div className="flex items-center justify-center h-[220px] text-base text-muted-foreground">
                        No graph data yet
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            </div>

            {/* ── Bottom row: Pending approvals + Recent activity ── */}
            <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Pending Approvals */}
              <div className="space-y-4">
                <SectionHeader title="Awaiting review" viewAllHref="/review" count={pendingApprovals} />
                {decisionsLoading ? (
                  <LoadingState rows={2} />
                ) : decisions && decisions.filter((d) => d.status === "proposed").length > 0 ? (
                  <div className="space-y-2.5">
                    {decisions
                      .filter((d) => d.status === "proposed")
                      .slice(0, 3)
                      .map((d) => (
                        <EntityCard
                          key={d.id}
                          id={d.id}
                          title={d.title}
                          status={d.status}
                          ownerName={d.owner_name}
                          href={`/decisions/${d.id}`}
                          compact
                        />
                      ))}
                  </div>
                ) : (
                  <div className="bg-card border border-border rounded-xl px-5 py-4 text-base text-muted-foreground">
                    No pending approvals
                  </div>
                )}
              </div>

              {/* Recent Agent Activity */}
              <div className="space-y-4">
                <SectionHeader title="Recent agent activity" viewAllHref="/audit" count={actions?.length} />
                {actionsLoading ? (
                  <LoadingState rows={3} />
                ) : actions && actions.length > 0 ? (
                  <div className="space-y-2">
                    {actions.slice(0, 5).map((action) => (
                      <div
                        key={action.id}
                        className="bg-card border border-border rounded-lg px-4 py-3 flex items-center justify-between gap-3"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="text-base font-medium text-foreground truncate">
                            {action.action_type}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            {action.initiated_by && (
                              <OwnerChip name={action.initiated_by} showName={false} />
                            )}
                            <span className="text-sm text-muted-foreground font-mono">
                              {action.initiated_by} · {new Date(action.timestamp).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <StatusBadge status={action.status} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-card border border-border rounded-xl px-5 py-4 text-base text-muted-foreground">
                    No actions yet
                  </div>
                )}
              </div>
            </motion.div>

            {/* ── What Changed — Recent Ingestion Jobs ─────────── */}
            {jobs && jobs.length > 0 && (
              <motion.div variants={itemVariants} className="space-y-4">
                <SectionHeader title="What changed" count={jobs.length} />
                <div className="space-y-2">
                  {jobs.slice(0, 5).map((job) => (
                    <Link
                      key={job.job_id}
                      href={`/jobs/${job.job_id}`}
                      className="bg-card border border-border rounded-lg px-5 py-3.5 flex items-center justify-between gap-3 hover:border-primary/30 transition-colors group"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {job.artifact_type ? (
                          <ArtifactTypeBadge type={job.artifact_type} />
                        ) : (
                          <Activity className="w-4 h-4 text-muted-foreground shrink-0" />
                        )}
                        <span className="text-base font-medium text-foreground truncate group-hover:text-primary transition-colors">
                          {job.artifact_title || job.meeting_title || "Untitled"}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-sm text-muted-foreground font-mono">
                          {new Date(job.created_at).toLocaleDateString()}
                        </span>
                        <StatusBadge status={job.status} />
                      </div>
                    </Link>
                  ))}
                </div>
              </motion.div>
            )}

            {/* ── Quick Nav ────────────────────────────────────── */}
            <motion.div variants={itemVariants} className="space-y-4">
              <SectionHeader title="Navigate" />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {QUICK_NAV.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <motion.div
                      key={item.href}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 + i * 0.04, duration: 0.2 }}
                      whileHover={{ y: -3 }}
                    >
                      <Link
                        href={item.href}
                        className="bg-card border border-border rounded-xl p-5 flex gap-3 items-start hover:border-primary/30 transition-all group hover:shadow-glow-sm"
                      >
                        <div className={`p-2.5 rounded-lg shrink-0 ${item.bg} transition-colors`}>
                          <Icon className={`w-5 h-5 ${item.accent} transition-colors`} />
                        </div>
                        <div className="min-w-0">
                          <div className="text-base font-medium text-foreground group-hover:text-primary transition-colors">{item.label}</div>
                          <div className="text-sm text-muted-foreground mt-1 leading-relaxed">{item.description}</div>
                        </div>
                      </Link>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          </div>

          {/* Context Rail — visible on large screens */}
          {decisions && actions && (
            <div className="hidden 2xl:block">
              <ContextRail decisions={decisions} actions={actions} />
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
