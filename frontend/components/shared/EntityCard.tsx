"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { StatusBadge } from "./StatusBadge";
import { OwnerChip } from "./OwnerChip";
import { cn } from "@/lib/utils";

interface EntityCardProps {
  id: string;
  title: string;
  summary?: string;
  status?: string;
  confidence?: number;
  ownerName?: string;
  meetingTitle?: string;
  href?: string;
  onClick?: () => void;
  compact?: boolean;
  className?: string;
}

export function EntityCard({
  id,
  title,
  summary,
  status,
  confidence,
  ownerName,
  meetingTitle,
  href,
  onClick,
  compact = false,
  className,
}: EntityCardProps) {
  const inner = (
    <motion.div
      whileHover={{ y: -1 }}
      transition={{ duration: 0.12, ease: "easeOut" }}
      className={cn(
        "bg-card border border-border rounded-xl group relative overflow-hidden transition-colors",
        "hover:border-primary/30",
        compact ? "p-3" : "p-4",
        className
      )}
    >
      {/* Hover left accent */}
      <div className="absolute left-0 top-3 bottom-3 w-0 group-hover:w-0.5 bg-primary rounded-r-full transition-all duration-150" />

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0 pl-1">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            {status && <StatusBadge status={status} />}
            <span className="text-xs text-muted-foreground/60 font-mono">{id}</span>
          </div>
          <div className="font-semibold text-foreground text-sm leading-snug group-hover:text-primary transition-colors">
            {title}
          </div>
          {summary && !compact && (
            <div className="text-xs text-muted-foreground mt-1.5 line-clamp-2 leading-relaxed">
              {summary}
            </div>
          )}
        </div>
        {confidence !== undefined && (
          <div className="text-right shrink-0">
            <div className="text-xs font-semibold text-foreground">{Math.round(confidence * 100)}%</div>
            <div className="w-14 h-1.5 bg-muted rounded-full mt-1 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary/70 to-primary"
                style={{ width: `${Math.round(confidence * 100)}%` }}
              />
            </div>
            <div className="text-xs text-muted-foreground/60 mt-0.5">confidence</div>
          </div>
        )}
      </div>

      {(ownerName || meetingTitle) && !compact && (
        <div className="flex items-center gap-3 pt-2 mt-2 border-t border-border/50">
          {ownerName && <OwnerChip name={ownerName} />}
          {meetingTitle && (
            <span className="text-xs text-muted-foreground truncate">
              {meetingTitle}
            </span>
          )}
        </div>
      )}
    </motion.div>
  );

  if (href) {
    return (
      <Link href={href} className="block rounded-xl">
        {inner}
      </Link>
    );
  }
  if (onClick) {
    return (
      <button onClick={onClick} className="w-full text-left rounded-xl">
        {inner}
      </button>
    );
  }
  return inner;
}
