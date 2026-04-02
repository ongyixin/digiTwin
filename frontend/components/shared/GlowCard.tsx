"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface GlowCardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: "primary" | "emerald" | "amber" | "crimson" | "none";
  hoverLift?: boolean;
  as?: "div" | "article";
}

const GLOW_SHADOW: Record<string, string> = {
  primary: "0 0 20px hsl(217 91% 60% / 0.18), 0 0 40px hsl(217 91% 60% / 0.08)",
  emerald: "0 0 20px hsl(158 64% 52% / 0.15)",
  amber: "0 0 20px hsl(38 92% 50% / 0.15)",
  crimson: "0 0 20px hsl(0 72% 51% / 0.15)",
  none: "none",
};

export function GlowCard({
  children,
  className,
  glowColor = "primary",
  hoverLift = true,
}: GlowCardProps) {
  return (
    <motion.div
      whileHover={
        hoverLift
          ? { y: -2, boxShadow: GLOW_SHADOW[glowColor] ?? GLOW_SHADOW.primary }
          : {}
      }
      transition={{ duration: 0.15, ease: "easeOut" }}
      className={cn(
        "bg-card border border-border rounded-xl transition-colors",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
