import { CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface PermissionBadgeProps {
  allowed: boolean;
  className?: string;
}

export function PermissionBadge({ allowed, className }: PermissionBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold",
        allowed
          ? "bg-emerald-500/12 text-emerald-400 border border-emerald-500/25"
          : "bg-red-500/12 text-red-400 border border-red-500/25",
        className
      )}
    >
      <span
        className={cn(
          "w-2 h-2 rounded-full shrink-0",
          allowed ? "bg-emerald-400 shadow-[0_0_6px_hsl(158_64%_52%/0.6)]" : "bg-red-400 shadow-[0_0_6px_hsl(0_72%_51%/0.6)]"
        )}
      />
      {allowed ? (
        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
      ) : (
        <XCircle className="w-3.5 h-3.5 shrink-0" />
      )}
      {allowed ? "Allowed" : "Denied"}
    </span>
  );
}
