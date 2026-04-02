"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface LoadingStateProps {
  rows?: number;
  className?: string;
}

function ShimmerRow({ delay }: { delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay }}
      className="bg-card border border-border rounded-xl p-4 space-y-2.5 overflow-hidden"
    >
      <div className="flex items-center gap-2">
        <div className="h-4 w-14 rounded-md animate-shimmer" />
        <div className="h-3 w-20 rounded animate-shimmer" />
      </div>
      <div className="h-4 w-3/4 rounded animate-shimmer" />
      <div className="h-3 w-1/2 rounded animate-shimmer" />
    </motion.div>
  );
}

export function LoadingState({ rows = 4, className }: LoadingStateProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <ShimmerRow key={i} delay={i * 0.05} />
      ))}
    </div>
  );
}
