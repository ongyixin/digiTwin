"use client";

import { GRAPH_NODE_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface GraphLegendProps {
  activeTypes: Set<string>;
  onToggle: (type: string) => void;
  typeCounts?: Record<string, number>;
  className?: string;
}

export function GraphLegend({ activeTypes, onToggle, typeCounts, className }: GraphLegendProps) {
  const types = Object.keys(GRAPH_NODE_COLORS).filter((t) => t !== "Node");

  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {types.map((type) => {
        const color = GRAPH_NODE_COLORS[type];
        const active = activeTypes.has(type);
        const count = typeCounts?.[type];
        return (
          <button
            key={type}
            onClick={() => onToggle(type)}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all duration-200",
              active
                ? "text-foreground"
                : "border-border text-muted-foreground opacity-30 hover:opacity-60"
            )}
            style={
              active
                ? {
                    background: color + "18",
                    borderColor: color + "50",
                    color,
                  }
                : undefined
            }
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0 transition-all"
              style={{
                background: active ? color : undefined,
                boxShadow: active ? `0 0 6px ${color}80` : undefined,
              }}
            />
            {type}
            {count !== undefined && count > 0 && (
              <span
                className="ml-0.5 opacity-60 font-mono"
                style={{ fontSize: "0.65rem" }}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
