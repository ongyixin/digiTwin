"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft, CheckCircle2, Clock, AlertTriangle, Loader2, Wifi, WifiOff,
} from "lucide-react";
import { useJobStream } from "@/lib/hooks";
import { PipelineDAG } from "@/components/pipeline/PipelineDAG";
import { TwinDiff } from "@/components/pipeline/TwinDiff";
import { ArtifactTypeBadge } from "@/components/shared/ArtifactTypeBadge";
import { MetricCard } from "@/components/shared/MetricCard";
import { PulseIndicator } from "@/components/shared/PulseIndicator";
import { cn } from "@/lib/utils";
import { GitBranch } from "lucide-react";

interface PageProps {
  params: { id: string };
}

function StatusBanner({ status, error }: { status: string; error?: string }) {
  const configs: Record<string, { cls: string; icon: React.ReactNode; label: string }> = {
    completed: {
      cls: "bg-emerald-500/10 border-emerald-500/25 text-emerald-400",
      icon: <CheckCircle2 className="w-4 h-4" />,
      label: "Ingestion complete",
    },
    failed: {
      cls: "bg-red-500/10 border-red-500/25 text-red-400",
      icon: <AlertTriangle className="w-4 h-4" />,
      label: error || "Ingestion failed",
    },
    running: {
      cls: "bg-blue-500/10 border-blue-500/25 text-blue-400",
      icon: <Loader2 className="w-4 h-4 animate-spin" />,
      label: "Processing…",
    },
  };
  const cfg = configs[status] ?? {
    cls: "bg-muted border-border text-muted-foreground",
    icon: <Clock className="w-4 h-4" />,
    label: "Queued",
  };
  return (
    <div className={cn("flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium relative overflow-hidden", cfg.cls)}>
      {status === "running" && (
        <div className="absolute inset-0 pointer-events-none" style={{
          background: "linear-gradient(90deg, transparent 0%, hsl(217 91% 60% / 0.05) 50%, transparent 100%)",
          backgroundSize: "200% 100%",
          animation: "shimmer 2s ease-in-out infinite",
        }} />
      )}
      {cfg.icon}
      {cfg.label}
    </div>
  );
}

export default function JobPage({ params }: PageProps) {
  const { id } = params;
  const { job, connected, error } = useJobStream(id);

  return (
    <motion.div
      className="max-w-5xl mx-auto p-6 lg:p-8 space-y-6"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      {/* Header */}
      <div className="space-y-3">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to dashboard
        </Link>

        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-xl font-bold text-foreground">Live Run Console</h1>
              {job?.artifact_type && (
                <ArtifactTypeBadge type={job.artifact_type} size="md" />
              )}
            </div>
            {job && (
              <p className="text-sm text-muted-foreground">
                {job.artifact_title || job.meeting_title || "Untitled"}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0 flex-wrap">
            <span className="flex items-center gap-1.5 text-xs font-mono">
              {connected ? (
                <>
                  <PulseIndicator color="emerald" size="sm" />
                  <span className="text-emerald-400">live</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3 h-3 text-muted-foreground" />
                  <span className="text-muted-foreground">polling</span>
                </>
              )}
            </span>
            {job && <StatusBanner status={job.status} error={job.error} />}
          </div>
        </div>
        <div className="gradient-rule" />
      </div>

      {!job ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading job…
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pipeline DAG */}
          <div
            className="border border-border rounded-xl p-5 space-y-4"
            style={{ background: "hsl(var(--surface-1, var(--card)))" }}
          >
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-[0.12em]">
              Pipeline Stages
            </h2>
            <PipelineDAG stages={job.stages} status={job.status} />

            {job.status === "completed" && Object.keys(job.entities_created).length > 0 && (
              <div className="pt-4 border-t border-border space-y-3">
                <p className="text-xs font-semibold text-muted-foreground">Entities Created</p>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(job.entities_created).map(([k, v]) => (
                    <MetricCard
                      key={k}
                      label={k}
                      value={v as number}
                      icon={GitBranch}
                      size="sm"
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Twin Diff */}
          <div
            className="border border-border rounded-xl p-5"
            style={{ background: "hsl(var(--surface-1, var(--card)))" }}
          >
            {job.twin_diff ? (
              <TwinDiff diff={job.twin_diff} />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center py-8 text-muted-foreground">
                {job.status === "running" || job.status === "queued" ? (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin mb-2" />
                    <p className="text-sm">Twin diff will appear here after ingestion…</p>
                  </>
                ) : (
                  <p className="text-sm">No diff available.</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Job metadata footer */}
      {job && (
        <div className="text-xs text-muted-foreground font-mono flex flex-wrap gap-4 pt-2 border-t border-border">
          <span>id: {job.job_id}</span>
          {job.artifact_id && <span>artifact: {job.artifact_id}</span>}
          {job.artifact_type && <span>type: {job.artifact_type}</span>}
          <span>started: {new Date(job.created_at).toLocaleString()}</span>
          {job.completed_at && <span>finished: {new Date(job.completed_at).toLocaleString()}</span>}
        </div>
      )}
    </motion.div>
  );
}
