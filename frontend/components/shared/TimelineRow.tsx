"use client";

import { LucideIcon } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { cn } from "@/lib/utils";

interface TimelineRowProps {
  timestamp: string;
  icon?: LucideIcon;
  title: string;
  subtitle?: string;
  status?: string;
  isLast?: boolean;
  onClick?: () => void;
  className?: string;
}

export function TimelineRow({
  timestamp,
  icon: Icon,
  title,
  subtitle,
  status,
  isLast,
  onClick,
  className,
}: TimelineRowProps) {
  const dotColor = (() => {
    if (!status) return "border-border bg-card";
    if (status === "approved" || status === "allowed") return "border-emerald-500/40 bg-emerald-500/10";
    if (status === "blocked" || status === "denied" || status === "contradicted") return "border-red-500/40 bg-red-500/10";
    if (status === "proposed" || status === "pending") return "border-amber-500/40 bg-amber-500/10";
    if (status === "active" || status === "running") return "border-primary/40 bg-primary/10";
    return "border-border bg-card";
  })();

  return (
    <div
      className={cn("flex gap-3 group", onClick && "cursor-pointer", className)}
      onClick={onClick}
    >
      {/* Spine */}
      <div className="flex flex-col items-center shrink-0">
        <div
          className={cn(
            "w-7 h-7 rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-150",
            dotColor,
            onClick && "group-hover:border-primary group-hover:bg-primary/15"
          )}
        >
          {Icon ? (
            <Icon className="w-3 h-3 text-muted-foreground group-hover:text-primary transition-colors" />
          ) : (
            <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground group-hover:bg-primary transition-colors" />
          )}
        </div>
        {!isLast && <div className="w-px flex-1 bg-border/60 mt-1 mb-1" />}
      </div>

      {/* Content */}
      <div className={cn("pb-4 flex-1 min-w-0", isLast && "pb-0")}>
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div className="flex-1 min-w-0">
            <div
              className={cn(
                "text-sm font-medium text-foreground transition-colors",
                onClick && "group-hover:text-primary"
              )}
            >
              {title}
            </div>
            {subtitle && <div className="text-xs text-muted-foreground mt-0.5">{subtitle}</div>}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {status && <StatusBadge status={status} />}
            <span className="font-mono text-xs text-muted-foreground whitespace-nowrap">{timestamp}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
