"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Inbox, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { useReviewInbox } from "@/lib/hooks";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { PageHeader } from "@/components/shared/PageHeader";
import { OwnerChip } from "@/components/shared/OwnerChip";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ReviewTask } from "@/lib/types";

const REVIEWER_ID = "admin";

function ReviewCard({ task, onResolved }: { task: ReviewTask; onResolved: () => void }) {
  const [loading, setLoading] = useState<"approve" | "reject" | null>(null);
  const [done, setDone] = useState<"approved" | "rejected" | null>(null);
  const [error, setError] = useState("");

  async function handle(approve: boolean) {
    setLoading(approve ? "approve" : "reject");
    setError("");
    try {
      await api.approveReview(task.id, REVIEWER_ID);
      setDone(approve ? "approved" : "rejected");
      setTimeout(onResolved, 1000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.2 }}
      className="bg-card border border-border rounded-xl p-4 space-y-3 relative overflow-hidden"
    >
      {/* Amber left accent */}
      <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-amber-500 rounded-r-full" />

      <div className="flex items-start justify-between gap-3 pl-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span className="text-sm font-semibold text-foreground truncate">{task.action_type}</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{task.reason}</p>
          <div className="flex items-center gap-3 mt-2">
            <OwnerChip name={task.initiated_by} />
            <span className="text-xs text-muted-foreground font-mono">
              {new Date(task.created_at).toLocaleDateString()}
            </span>
            <span className="text-xs text-muted-foreground/50 font-mono">{task.id}</span>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-1.5">
          <AnimatePresence mode="wait">
            {done === "approved" ? (
              <motion.span
                key="approved"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-1 text-xs text-emerald-400 font-medium"
              >
                <CheckCircle2 className="w-4 h-4" /> Approved
              </motion.span>
            ) : done === "rejected" ? (
              <motion.span
                key="rejected"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-1 text-xs text-red-400 font-medium"
              >
                <XCircle className="w-4 h-4" /> Rejected
              </motion.span>
            ) : (
              <motion.div key="actions" className="flex gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs gap-1 text-red-400 border-red-400/25 hover:bg-red-400/10 hover:border-red-400/50 transition-all"
                  disabled={!!loading}
                  onClick={() => handle(false)}
                >
                  {loading === "reject" ? "…" : <><XCircle className="w-3.5 h-3.5" /> Reject</>}
                </Button>
                <Button
                  size="sm"
                  className="h-7 text-xs gap-1 hover:shadow-glow-sm transition-shadow"
                  disabled={!!loading}
                  onClick={() => handle(true)}
                >
                  {loading === "approve" ? "…" : <><CheckCircle2 className="w-3.5 h-3.5" /> Approve</>}
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/25 rounded-lg px-3 py-2 ml-3">
          {error}
        </p>
      )}
    </motion.div>
  );
}

export default function ReviewPage() {
  const { data: tasks, isLoading, refetch } = useReviewInbox();
  const pendingCount = tasks?.length ?? 0;

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-3xl mx-auto">
      <PageHeader
        icon={Inbox}
        title="Review Inbox"
        subtitle="Approve or reject blocked agent actions to re-run them with updated permissions"
        actions={
          pendingCount > 0 ? (
            <span className="bg-amber-500/15 text-amber-400 border border-amber-500/25 text-xs font-semibold px-2.5 py-1 rounded-lg">
              {pendingCount} pending
            </span>
          ) : undefined
        }
      />

      {isLoading ? (
        <LoadingState rows={3} />
      ) : !tasks || tasks.length === 0 ? (
        <EmptyState
          title="Inbox is empty"
          description="Blocked agent actions will appear here for review."
        />
      ) : (
        <AnimatePresence>
          <div className="space-y-3">
            {tasks.map((task) => (
              <ReviewCard key={task.id} task={task} onResolved={() => refetch()} />
            ))}
          </div>
        </AnimatePresence>
      )}
    </div>
  );
}
