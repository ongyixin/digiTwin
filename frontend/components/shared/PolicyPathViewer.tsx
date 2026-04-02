import { cn } from "@/lib/utils";

interface PolicyPathViewerProps {
  path: string[];
  className?: string;
  compact?: boolean;
}

export function PolicyPathViewer({ path, className, compact = false }: PolicyPathViewerProps) {
  if (!path || path.length === 0) {
    return <span className="text-xs text-muted-foreground">No policy path</span>;
  }

  if (compact && path.length > 3) {
    const truncated = path.slice(0, 2);
    return (
      <div className={cn("flex items-center gap-1 flex-wrap", className)}>
        {truncated.map((step, i) => (
          <span key={i} className="flex items-center gap-1">
            <span className="font-mono text-xs px-1.5 py-0.5 rounded border bg-muted/40 text-muted-foreground border-border">
              {step}
            </span>
            {i < truncated.length - 1 && (
              <span className="text-muted-foreground/40 text-xs">›</span>
            )}
          </span>
        ))}
        <span className="text-xs text-muted-foreground/50 font-mono">
          …+{path.length - 2}
        </span>
      </div>
    );
  }

  return (
    <div className={cn("flex items-center flex-wrap gap-1", className)}>
      {path.map((step, i) => (
        <span key={i} className="flex items-center gap-1">
          <span
            className={cn(
              "font-mono px-2 py-0.5 rounded-md border transition-colors hover:text-foreground",
              "bg-muted/40 border-border text-muted-foreground",
              i % 2 === 0
                ? "border-l-2 border-l-primary/30"
                : "border-l-2 border-l-muted-foreground/20",
              compact ? "text-xs px-1.5" : "text-sm"
            )}
          >
            {step}
          </span>
          {i < path.length - 1 && (
            <span className="text-muted-foreground/40 text-sm">›</span>
          )}
        </span>
      ))}
    </div>
  );
}
