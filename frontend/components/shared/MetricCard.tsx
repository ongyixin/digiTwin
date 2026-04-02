"use client";

import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: number | string;
  icon: LucideIcon;
  trend?: string;
  description?: string;
  accent?: "blue" | "emerald" | "amber" | "crimson" | "violet" | "default";
  size?: "lg" | "md" | "sm";
  className?: string;
}

const ACCENT: Record<string, { icon: string; bar: string; glow: string }> = {
  blue:    { icon: "text-blue-400 bg-blue-500/10",    bar: "bg-blue-500",    glow: "hover:shadow-glow-sm" },
  emerald: { icon: "text-emerald-400 bg-emerald-500/10", bar: "bg-emerald-500", glow: "hover:shadow-glow-emerald" },
  amber:   { icon: "text-amber-400 bg-amber-500/10",  bar: "bg-amber-500",   glow: "hover:shadow-glow-amber" },
  crimson: { icon: "text-red-400 bg-red-500/10",      bar: "bg-red-500",     glow: "hover:shadow-glow-crimson" },
  violet:  { icon: "text-violet-400 bg-violet-500/10", bar: "bg-violet-500", glow: "hover:shadow-glow-sm" },
  default: { icon: "text-muted-foreground bg-muted/50", bar: "bg-muted-foreground", glow: "" },
};

export function MetricCard({
  label,
  value,
  icon: Icon,
  trend,
  description,
  accent = "default",
  size = "md",
  className,
}: MetricCardProps) {
  const a = ACCENT[accent] ?? ACCENT.default;

  if (size === "sm") {
    return (
      <div
        className={cn(
          "bg-card border border-border rounded-lg px-3 py-2 flex items-center gap-2.5",
          a.glow,
          "transition-shadow",
          className
        )}
      >
        <div className={cn("p-1.5 rounded-md shrink-0", a.icon)}>
          <Icon className="w-3 h-3" />
        </div>
        <div className="min-w-0">
          <div className="text-base font-bold text-foreground leading-none">{value}</div>
          <div className="text-xs text-muted-foreground mt-0.5 truncate">{label}</div>
        </div>
      </div>
    );
  }

  if (size === "lg") {
    return (
      <motion.div
        whileHover={{ y: -2 }}
        transition={{ duration: 0.15, ease: "easeOut" }}
        className={cn(
          "bg-card border border-border rounded-xl p-5 relative overflow-hidden",
          a.glow,
          "transition-shadow",
          className
        )}
      >
        {/* Accent left bar */}
        <div className={cn("absolute left-0 top-4 bottom-4 w-0.5 rounded-r-full", a.bar)} />
        <div className="flex items-start justify-between gap-4 pl-3">
          <div className="flex-1 min-w-0">
            <div className="text-xs text-muted-foreground font-medium mb-2">{label}</div>
            <div className="text-4xl font-bold text-foreground leading-none mb-2">{value}</div>
            {description && (
              <div className="text-xs text-muted-foreground">{description}</div>
            )}
            {trend && (
              <div className="text-xs text-muted-foreground mt-1">{trend}</div>
            )}
          </div>
          <div className={cn("p-2.5 rounded-xl shrink-0", a.icon)}>
            <Icon className="w-5 h-5" />
          </div>
        </div>
      </motion.div>
    );
  }

  /* md (default) */
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      className={cn(
        "bg-card border border-border rounded-xl p-4 relative overflow-hidden",
        a.glow,
        "transition-shadow",
        className
      )}
    >
      {/* Thin accent top border */}
      <div className={cn("absolute top-0 left-4 right-4 h-px rounded-full opacity-60", a.bar)} />
      <div className="flex items-start justify-between gap-3 pt-1">
        <div>
          <div className="text-xs text-muted-foreground font-medium mb-1">{label}</div>
          <div className="text-2xl font-bold text-foreground">{value}</div>
          {description && (
            <div className="text-xs text-muted-foreground mt-0.5">{description}</div>
          )}
          {trend && <div className="text-xs text-muted-foreground mt-1">{trend}</div>}
        </div>
        <div className={cn("p-2 rounded-lg shrink-0", a.icon)}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
    </motion.div>
  );
}
