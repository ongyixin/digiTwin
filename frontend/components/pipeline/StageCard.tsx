"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StageInfo } from "@/lib/types";

const STAGE_LABELS: Record<string, string> = {
  setup: "Setup",
  chunking: "Chunking",
  entity_extraction: "Entity Extraction",
  relationship_extraction: "Relationship Extraction",
  embedding: "Embedding",
  graph_upsert: "Graph Upsert",
  twin_diff: "Twin Diff",
};

interface StageCardProps {
  stage: StageInfo;
  isLast?: boolean;
}

export function StageCard({ stage, isLast = false }: StageCardProps) {
  const label = STAGE_LABELS[stage.name] ?? stage.name;

  const icon =
    stage.status === "completed" ? (
      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
    ) : stage.status === "running" ? (
      <Loader2 className="w-5 h-5 text-blue-400 shrink-0 animate-spin" />
    ) : stage.status === "failed" ? (
      <XCircle className="w-5 h-5 text-red-400 shrink-0" />
    ) : (
      <Circle className="w-5 h-5 text-muted-foreground/40 shrink-0" />
    );

  return (
    <div className="flex gap-3">
      {/* Left: icon + connector */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "flex items-center justify-center w-9 h-9 rounded-full border-2 transition-colors duration-300",
            stage.status === "completed" && "border-emerald-500/60 bg-emerald-500/10",
            stage.status === "running" && "border-blue-500/60 bg-blue-500/10",
            stage.status === "failed" && "border-red-500/60 bg-red-500/10",
            stage.status === "pending" && "border-border bg-card"
          )}
        >
          {icon}
        </div>
        {!isLast && (
          <div
            className={cn(
              "w-0.5 flex-1 min-h-[24px] transition-colors duration-500",
              stage.status === "completed" ? "bg-emerald-500/40" : "bg-border"
            )}
          />
        )}
      </div>

      {/* Right: content */}
      <div className="pb-6 flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-0.5">
          <span
            className={cn(
              "text-sm font-semibold",
              stage.status === "running" && "text-blue-400",
              stage.status === "completed" && "text-foreground",
              stage.status === "failed" && "text-red-400",
              stage.status === "pending" && "text-muted-foreground"
            )}
          >
            {label}
          </span>
          {stage.duration_ms !== undefined && stage.duration_ms !== null && (
            <span className="text-xs text-muted-foreground font-mono shrink-0">
              {stage.duration_ms}ms
            </span>
          )}
        </div>

        {stage.detail && stage.status === "running" && (
          <p className="text-xs text-muted-foreground mt-0.5">{stage.detail}</p>
        )}

        {stage.status === "completed" && stage.entities_found > 0 && (
          <p className="text-xs text-muted-foreground mt-0.5">
            {stage.entities_found} entities processed
          </p>
        )}
      </div>
    </div>
  );
}
