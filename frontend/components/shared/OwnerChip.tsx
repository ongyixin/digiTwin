import { cn } from "@/lib/utils";

function nameToHue(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % 360;
}

interface OwnerChipProps {
  name: string;
  showName?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export function OwnerChip({ name, showName = true, size = "sm", className }: OwnerChipProps) {
  const hue = nameToHue(name);
  const initials = name
    .split(/[\s_-]/)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .slice(0, 2)
    .join("");

  const avatarSize = size === "sm" ? "w-4 h-4 text-xs" : "w-5 h-5 text-xs";

  return (
    <span className={cn("inline-flex items-center gap-1 shrink-0", className)}>
      <span
        className={cn("rounded-full flex items-center justify-center font-semibold shrink-0", avatarSize)}
        style={{
          background: `hsl(${hue} 55% 30%)`,
          color: `hsl(${hue} 70% 75%)`,
        }}
      >
        {initials || "?"}
      </span>
      {showName && (
        <span className="text-sm text-muted-foreground">{name}</span>
      )}
    </span>
  );
}
