"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { GitBranch, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import type { Decision } from "@/lib/types";
import { cn } from "@/lib/utils";

interface TimelineDecision extends Decision {
  contradictions?: number;
}

interface TimelineViewProps {
  decisions: TimelineDecision[];
}

export function TimelineView({ decisions }: TimelineViewProps) {
  const [scrubIndex, setScrubIndex] = useState(decisions.length - 1);

  const visibleDecisions = useMemo(
    () => decisions.slice(0, scrubIndex + 1),
    [decisions, scrubIndex]
  );

  const activeDecision = decisions[scrubIndex];

  return (
    <div className="space-y-6">
      {/* Scrubber */}
      <div
        className="border border-border rounded-xl p-4 space-y-3 relative overflow-hidden"
        style={{ background: "hsl(var(--surface-1, var(--card)))" }}
      >
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-primary/40 to-transparent" />
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-muted-foreground">Scrubber</span>
          <span className="text-xs text-muted-foreground font-mono">
            {scrubIndex + 1} / {decisions.length}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={Math.max(0, decisions.length - 1)}
          value={scrubIndex}
          onChange={(e) => setScrubIndex(Number(e.target.value))}
          className="w-full accent-primary cursor-pointer"
          style={{ height: "3px" }}
        />
        {activeDecision && (
          <div className="flex items-center gap-2 text-xs text-foreground">
            <Clock className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="font-mono text-muted-foreground">
              {activeDecision.created_at
                ? new Date(activeDecision.created_at).toLocaleDateString()
                : "—"}
            </span>
            <span className="font-medium text-foreground">{activeDecision.title}</span>
          </div>
        )}
      </div>

      {/* Decision list that grows as you scrub */}
      <div className="relative">
        {/* Vertical timeline spine */}
        <div className="absolute left-4 top-0 bottom-0 w-px bg-border/70" />

        <div className="space-y-2 pl-10">
          <AnimatePresence initial={false}>
            {visibleDecisions.map((d, i) => (
              <motion.div
                key={d.id}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25, delay: i === scrubIndex ? 0 : 0 }}
              >
                <TimelineDecisionCard
                  decision={d}
                  isActive={i === scrubIndex}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function TimelineDecisionCard({
  decision,
  isActive,
}: {
  decision: TimelineDecision;
  isActive: boolean;
}) {
  const contradictions = (decision as any).contradictions ?? 0;

  return (
    <Link href={`/decisions/${decision.id}`}>
      <div
        className={cn(
          "relative bg-card border rounded-xl p-3.5 transition-all duration-150 hover:border-primary/30",
          isActive
            ? "border-primary/40 shadow-glow-sm"
            : "border-border"
        )}
      >
        {isActive && (
          <div className="absolute left-0 top-2 bottom-2 w-0.5 bg-primary rounded-r-full" />
        )}
        {/* Dot on spine */}
        <div
          className={cn(
            "absolute -left-[26px] top-1/2 -translate-y-1/2 rounded-full border-2 transition-all",
            isActive
              ? "w-3.5 h-3.5 border-primary bg-primary shadow-[0_0_8px_hsl(217_91%_60%/0.6)]"
              : contradictions > 0
              ? "w-3 h-3 border-amber-400 bg-amber-400/20"
              : decision.status === "approved"
              ? "w-3 h-3 border-emerald-500 bg-emerald-500/20"
              : "w-3 h-3 border-border bg-muted"
          )}
        />

        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-0.5">
              <GitBranch className="w-3 h-3 text-muted-foreground shrink-0" />
              <span className="text-xs font-semibold text-foreground truncate">
                {decision.title}
              </span>
            </div>
            {decision.summary && (
              <p className="text-sm text-muted-foreground line-clamp-2 mt-0.5">
                {decision.summary}
              </p>
            )}
            <div className="flex items-center gap-3 mt-1.5">
              {decision.owner_name && (
                <span className="text-xs text-muted-foreground font-medium">
                  {decision.owner_name}
                </span>
              )}
              {decision.meeting_title && (
                <span className="text-xs text-muted-foreground truncate">
                  {decision.meeting_title}
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-col items-end gap-1 shrink-0">
            {contradictions > 0 && (
              <span className="flex items-center gap-1 text-xs text-amber-400 font-medium">
                <AlertTriangle className="w-3 h-3" />
                {contradictions} contradiction{contradictions !== 1 ? "s" : ""}
              </span>
            )}
            {decision.status === "approved" && (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <CheckCircle2 className="w-3 h-3" />
                approved
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
