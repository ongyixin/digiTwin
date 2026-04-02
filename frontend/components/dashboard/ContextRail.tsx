"use client";

import Link from "next/link";
import { AlertTriangle, Shield, ArrowRight } from "lucide-react";
import { PolicyPathViewer } from "@/components/shared/PolicyPathViewer";
import { PulseIndicator } from "@/components/shared/PulseIndicator";
import type { Decision, AgentAction } from "@/lib/types";

interface ContextRailProps {
  decisions: Decision[];
  actions: AgentAction[];
  onIngest?: () => void;
}

export function ContextRail({ decisions, actions }: ContextRailProps) {
  const blocked = actions.filter((a) => a.status === "blocked" || a.status === "denied");
  const latestBlocker = blocked[0] ?? null;
  const pending = decisions.filter((d) => d.status === "proposed");
  const latestAction = actions[0] ?? null;

  return (
    <aside className="w-[280px] shrink-0 space-y-4">
      {/* Top Blocker */}
      {latestBlocker ? (
        <div className="bg-card border border-red-500/20 rounded-xl p-4 space-y-2.5">
          <div className="flex items-center gap-2">
            <PulseIndicator color="crimson" pulse />
            <span className="text-xs font-semibold text-red-400">Top Blocker</span>
          </div>
          <div className="text-xs font-medium text-foreground">{latestBlocker.action_type}</div>
          {latestBlocker.policy_path && latestBlocker.policy_path.length > 0 && (
            <PolicyPathViewer path={latestBlocker.policy_path} compact />
          )}
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1.5">
            <PulseIndicator color="emerald" />
            <span className="text-xs font-semibold text-emerald-400">No Blockers</span>
          </div>
          <div className="text-sm text-muted-foreground">All recent actions are allowed</div>
        </div>
      )}

      {/* Latest Policy Path */}
      {latestAction?.policy_path && latestAction.policy_path.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Shield className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-xs font-semibold text-foreground">Latest Policy Path</span>
          </div>
          <PolicyPathViewer path={latestAction.policy_path} compact />
        </div>
      )}

      {/* Recommended Next Step */}
      <div className="bg-card border border-border rounded-xl p-4 space-y-2.5">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-xs font-semibold text-foreground">Recommended</span>
        </div>
        {pending.length > 0 ? (
          <Link
            href="/review"
            className="flex items-center justify-between gap-2 group"
          >
            <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
              Review {pending.length} pending approval{pending.length !== 1 ? "s" : ""}
            </span>
            <ArrowRight className="w-3 h-3 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
          </Link>
        ) : (
          <div className="text-sm text-muted-foreground">
            Ingest a new meeting to enrich the knowledge graph
          </div>
        )}
      </div>
    </aside>
  );
}
