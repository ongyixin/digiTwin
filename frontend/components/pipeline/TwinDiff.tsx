"use client";

import Link from "next/link";
import {
  GitBranch, Lightbulb, FileText, CheckSquare, Stamp, AlertTriangle,
} from "lucide-react";
import type { TwinDiff as TwinDiffType, TwinDiffItem } from "@/lib/types";
import { cn } from "@/lib/utils";

interface DiffSectionProps {
  label: string;
  items: TwinDiffItem[];
  icon: React.ElementType;
  variant: "new" | "warning";
  emptyText?: string;
}

function DiffSection({ label, items, icon: Icon, variant, emptyText }: DiffSectionProps) {
  if (items.length === 0 && !emptyText) return null;
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Icon
          className={cn(
            "w-3.5 h-3.5",
            variant === "new" ? "text-emerald-400" : "text-amber-400"
          )}
        />
        <span className="text-xs font-semibold text-foreground">{label}</span>
        {items.length > 0 && (
          <span
            className={cn(
              "text-xs font-mono px-1.5 py-0.5 rounded-full",
              variant === "new"
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-amber-500/15 text-amber-400"
            )}
          >
            +{items.length}
          </span>
        )}
      </div>
      {items.length === 0 ? (
        emptyText ? (
          <p className="text-xs text-muted-foreground pl-5">{emptyText}</p>
        ) : null
      ) : (
        <ul className="space-y-1 pl-5">
          {items.map((item) => (
            <li key={item.id} className="text-xs">
              {item.href ? (
                <Link
                  href={item.href}
                  className="text-primary hover:underline truncate block"
                >
                  {item.title}
                </Link>
              ) : (
                <span className="text-muted-foreground truncate block">{item.title}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface TwinDiffProps {
  diff: TwinDiffType;
}

export function TwinDiff({ diff }: TwinDiffProps) {
  const totalNew =
    diff.new_decisions.length +
    diff.new_assumptions.length +
    diff.new_evidence.length +
    diff.new_tasks.length +
    diff.new_approvals.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-foreground">Twin Diff</h3>
        <span className="text-xs text-muted-foreground font-mono">
          {totalNew} new · {diff.superseded_assumptions.length} superseded
        </span>
      </div>

      {/* Summary bar */}
      <div className="flex gap-1 h-1.5 rounded-full overflow-hidden bg-border">
        {diff.new_decisions.length > 0 && (
          <div
            className="bg-blue-500"
            style={{ flex: diff.new_decisions.length }}
          />
        )}
        {diff.new_assumptions.length > 0 && (
          <div
            className="bg-purple-500"
            style={{ flex: diff.new_assumptions.length }}
          />
        )}
        {diff.new_evidence.length > 0 && (
          <div
            className="bg-teal-500"
            style={{ flex: diff.new_evidence.length }}
          />
        )}
        {diff.superseded_assumptions.length > 0 && (
          <div
            className="bg-amber-500"
            style={{ flex: diff.superseded_assumptions.length }}
          />
        )}
      </div>

      <div className="space-y-4">
        <DiffSection
          label="New Decisions"
          items={diff.new_decisions}
          icon={GitBranch}
          variant="new"
        />
        <DiffSection
          label="New Assumptions"
          items={diff.new_assumptions}
          icon={Lightbulb}
          variant="new"
        />
        <DiffSection
          label="New Evidence"
          items={diff.new_evidence}
          icon={FileText}
          variant="new"
        />
        <DiffSection
          label="New Tasks"
          items={diff.new_tasks}
          icon={CheckSquare}
          variant="new"
        />
        <DiffSection
          label="New Approvals"
          items={diff.new_approvals}
          icon={Stamp}
          variant="new"
        />
        <DiffSection
          label="Superseded Assumptions"
          items={diff.superseded_assumptions}
          icon={AlertTriangle}
          variant="warning"
        />
      </div>

      {totalNew === 0 && diff.superseded_assumptions.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">
          No changes detected in this run.
        </p>
      )}
    </div>
  );
}
