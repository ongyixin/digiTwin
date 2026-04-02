import { cn } from "@/lib/utils";
import { FileText, FileAudio, FileVideo, Github, Shield, Layout } from "lucide-react";
import type { ArtifactType } from "@/lib/types";

interface TypeConfig {
  label: string;
  icon: React.ElementType;
  color: string;
  bg: string;
}

export const ARTIFACT_TYPE_CONFIG: Record<string, TypeConfig> = {
  transcript: {
    label: "Transcript",
    icon: FileText,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  policy_doc: {
    label: "Policy",
    icon: Shield,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
  prd: {
    label: "PRD",
    icon: Layout,
    color: "text-violet-400",
    bg: "bg-violet-500/10",
  },
  audio: {
    label: "Audio",
    icon: FileAudio,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  video: {
    label: "Video",
    icon: FileVideo,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  github_repo: {
    label: "GitHub",
    icon: Github,
    color: "text-zinc-300",
    bg: "bg-zinc-500/10",
  },
  generic_text: {
    label: "Text",
    icon: FileText,
    color: "text-muted-foreground",
    bg: "bg-muted/60",
  },
};

interface ArtifactTypeBadgeProps {
  type: ArtifactType | string;
  showLabel?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export function ArtifactTypeBadge({
  type,
  showLabel = true,
  size = "sm",
  className,
}: ArtifactTypeBadgeProps) {
  const cfg = ARTIFACT_TYPE_CONFIG[type] ?? ARTIFACT_TYPE_CONFIG.generic_text;
  const Icon = cfg.icon;
  const iconSize = size === "sm" ? "w-3 h-3" : "w-4 h-4";
  const padSize = size === "sm" ? "p-1" : "p-1.5";

  return (
    <span className={cn("inline-flex items-center gap-1.5 shrink-0", className)}>
      <span className={cn("rounded flex items-center justify-center", cfg.bg, padSize)}>
        <Icon className={cn(iconSize, cfg.color)} />
      </span>
      {showLabel && (
        <span className={cn("font-medium", cfg.color, size === "sm" ? "text-sm" : "text-xs")}>
          {cfg.label}
        </span>
      )}
    </span>
  );
}
