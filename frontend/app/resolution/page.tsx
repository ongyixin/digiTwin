"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Crosshair, Activity, Clock, CheckCircle2, Eye } from "lucide-react";
import { useResolutionCases } from "@/lib/hooks";
import { PageHeader } from "@/components/shared/PageHeader";
import { MetricCard } from "@/components/shared/MetricCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { CyclingGraphBackground } from "@/components/dashboard/GraphBackgrounds";
import type { CaseStatus } from "@/lib/types";

const STATUS_TABS: { label: string; value: CaseStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Planning", value: "planning" },
  { label: "Awaiting Review", value: "awaiting_review" },
  { label: "Monitoring", value: "monitoring" },
  { label: "Resolved", value: "resolved" },
];

const CASE_TYPE_LABELS: Record<string, string> = {
  launch_blocker: "Launch Blocker",
  contradiction: "Contradiction",
  stale_approval: "Stale Approval",
  dependency_cluster: "Dependency Cluster",
  policy_conflict: "Policy Conflict",
};

const listVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04 } },
};
const rowVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0 },
};

export default function ResolutionCenterPage() {
  const { data: cases, isLoading } = useResolutionCases();
  const [statusFilter, setStatusFilter] = useState<CaseStatus | "all">("all");

  const stats = useMemo(() => {
    if (!cases) return null;
    return {
      active: cases.filter((c) => ["planning", "executing"].includes(c.status)).length,
      awaiting_review: cases.filter((c) => c.status === "awaiting_review").length,
      monitoring: cases.filter((c) => c.status === "monitoring").length,
      resolved: cases.filter((c) => c.status === "resolved").length,
    };
  }, [cases]);

  const filtered = useMemo(() => {
    if (!cases) return [];
    if (statusFilter === "all") return cases;
    return cases.filter((c) => c.status === statusFilter);
  }, [cases, statusFilter]);

  return (
    <div className="relative">
      <CyclingGraphBackground opacity={0.3} />
      <div className="relative z-10 p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
        <PageHeader
          icon={Crosshair}
          title="Resolution Center"
          subtitle="Autonomous resolution cases for blockers, contradictions, and stale approvals"
        />

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MetricCard label="Active" value={stats.active} icon={Activity} accent="blue" size="sm" />
            <MetricCard label="Awaiting Review" value={stats.awaiting_review} icon={Clock} accent="amber" size="sm" />
            <MetricCard label="Monitoring" value={stats.monitoring} icon={Eye} accent="violet" size="sm" />
            <MetricCard label="Resolved" value={stats.resolved} icon={CheckCircle2} accent="emerald" size="sm" />
          </div>
        )}

        {/* Status tabs */}
        <div className="flex items-center gap-1 border-b border-border">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setStatusFilter(tab.value)}
              className={[
                "px-3 py-2 text-xs font-medium transition-colors relative",
                statusFilter === tab.value
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              ].join(" ")}
            >
              {tab.label}
              {statusFilter === tab.value && (
                <motion.div
                  layoutId="resolution-tab-indicator"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-500 rounded-full"
                />
              )}
            </button>
          ))}
        </div>

        {isLoading ? (
          <LoadingState rows={4} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title={cases?.length === 0 ? "No resolution cases" : "No cases match your filter"}
            description={
              cases?.length === 0
                ? 'Click "Resolve This" on any decision or approval to create a case.'
                : "Try selecting a different status filter."
            }
            action={
              statusFilter !== "all" ? (
                <button
                  onClick={() => setStatusFilter("all")}
                  className="text-xs text-orange-400 hover:underline"
                >
                  Show all cases
                </button>
              ) : undefined
            }
          />
        ) : (
          <motion.div
            className="space-y-2"
            initial="hidden"
            animate="visible"
            variants={listVariants}
          >
            {filtered.map((c) => (
              <motion.div key={c.case_id} variants={rowVariants}>
                <Link href={`/resolution/${c.case_id}`}>
                  <div className="bg-card border border-border rounded-xl p-4 hover:border-orange-500/30 transition-colors group">
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                          <StatusBadge status={c.status} />
                          <SeverityBadge severity={c.severity} />
                          <span className="text-xs text-muted-foreground bg-muted/40 px-2 py-0.5 rounded-md">
                            {CASE_TYPE_LABELS[c.case_type] ?? c.case_type}
                          </span>
                        </div>
                        <h3 className="text-sm font-semibold text-foreground group-hover:text-orange-400 transition-colors truncate">
                          {c.title}
                        </h3>
                        <div className="text-xs text-muted-foreground mt-1 font-mono">
                          {c.case_id} · {c.autonomy_mode} · {new Date(c.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <Crosshair className="w-4 h-4 text-muted-foreground/40 group-hover:text-orange-400 transition-colors shrink-0 mt-1" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  );
}
