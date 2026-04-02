"use client";

import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  compact?: boolean;
  className?: string;
}

export function PageHeader({
  icon: Icon,
  title,
  subtitle,
  actions,
  compact = false,
  className,
}: PageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn("space-y-3", className)}
    >
      <div className={cn("flex items-center justify-between gap-4", compact && "gap-3")}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 rounded-xl bg-primary/10 border border-primary/20 shrink-0">
            <Icon className={cn("text-primary", compact ? "w-4 h-4" : "w-5 h-5")} />
          </div>
          <div className="min-w-0">
            <h1 className={cn("font-semibold text-foreground leading-tight", compact ? "text-base" : "text-2xl")}>
              {title}
            </h1>
            {subtitle && !compact && (
              <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
        {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
      </div>
      {!compact && <div className="gradient-rule" />}
    </motion.div>
  );
}
