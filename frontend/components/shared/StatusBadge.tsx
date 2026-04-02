import { cn } from "@/lib/utils";
import { STATUS_COLORS } from "@/lib/constants";
import { PulseIndicator } from "./PulseIndicator";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const PULSE_STATUSES = new Set(["blocked", "denied", "pending", "proposed"]);

function dotColor(status: string): "primary" | "emerald" | "amber" | "crimson" | "muted" {
  if (status === "approved" || status === "allowed" || status === "validated") return "emerald";
  if (status === "proposed" || status === "pending") return "amber";
  if (status === "blocked" || status === "denied" || status === "rejected" || status === "contradicted") return "crimson";
  if (status === "active" || status === "running") return "primary";
  return "muted";
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const colors = STATUS_COLORS[status] ?? {
    bg: "bg-zinc-500/15",
    text: "text-zinc-400",
    border: "border-zinc-500/30",
  };
  const shouldPulse = PULSE_STATUSES.has(status);
  const dot = dotColor(status);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-sm font-medium",
        colors.text,
        className
      )}
    >
      <PulseIndicator color={dot} pulse={shouldPulse} size="sm" />
      {status}
    </span>
  );
}
