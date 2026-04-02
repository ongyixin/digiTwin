import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 px-8 text-center rounded-xl border border-border relative overflow-hidden",
        className
      )}
      style={{
        background: "radial-gradient(ellipse at center, hsl(var(--card)) 0%, hsl(var(--background)) 100%)",
      }}
    >
      {/* Shimmer sweep */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, hsl(var(--primary)/0.03) 50%, transparent 100%)",
          backgroundSize: "200% 100%",
          animation: "shimmer 3s ease-in-out infinite",
        }}
      />

      <div className="relative">
        {Icon && (
          <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
            <Icon className="w-5 h-5 text-muted-foreground" />
          </div>
        )}
        <div className="text-sm font-semibold text-foreground">{title}</div>
        {description && (
          <div className="text-xs text-muted-foreground mt-1.5 max-w-xs leading-relaxed">{description}</div>
        )}
        {action && <div className="mt-5">{action}</div>}
      </div>
    </div>
  );
}
