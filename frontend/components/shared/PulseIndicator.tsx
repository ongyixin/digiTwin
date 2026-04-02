import { cn } from "@/lib/utils";

interface PulseIndicatorProps {
  color?: "primary" | "emerald" | "amber" | "crimson" | "muted";
  size?: "sm" | "md";
  pulse?: boolean;
  className?: string;
}

const COLOR_CLASSES: Record<string, string> = {
  primary: "bg-primary",
  emerald: "bg-emerald-400",
  amber: "bg-amber-400",
  crimson: "bg-red-400",
  muted: "bg-muted-foreground",
};

export function PulseIndicator({
  color = "emerald",
  size = "sm",
  pulse = true,
  className,
}: PulseIndicatorProps) {
  const colorClass = COLOR_CLASSES[color] ?? COLOR_CLASSES.emerald;
  const sizeClass = size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2";

  return (
    <span
      className={cn(
        "rounded-full inline-block shrink-0",
        colorClass,
        sizeClass,
        pulse && "animate-pulse-dot",
        className
      )}
    />
  );
}
