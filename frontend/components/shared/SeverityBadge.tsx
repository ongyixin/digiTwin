import { cn } from "@/lib/utils";
import { SEVERITY_COLORS } from "@/lib/constants";

interface SeverityBadgeProps {
  severity: string;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const colors = SEVERITY_COLORS[severity] ?? {
    bg: "bg-zinc-500/15",
    text: "text-zinc-400",
    border: "border-zinc-500/30",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border",
        colors.bg,
        colors.text,
        colors.border,
        className
      )}
    >
      {severity}
    </span>
  );
}
