"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import type { Decision } from "@/lib/types";

const STATUS_COLOR: Record<string, string> = {
  proposed: "#f59e0b",
  approved: "#10b981",
  superseded: "#64748b",
  rejected: "#ef4444",
  active: "#3b82f6",
};

function hashStr(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = (h * 33) ^ s.charCodeAt(i);
  return Math.abs(h);
}

interface Node {
  id: string;
  x: number;
  y: number;
  color: string;
  label: string;
  status: string;
}

interface Edge {
  source: string;
  target: string;
}

function buildGraph(decisions: Decision[], width: number, height: number) {
  const nodes: Node[] = decisions.slice(0, 12).map((d, i) => {
    const angle = (i / Math.min(decisions.length, 12)) * 2 * Math.PI;
    const r = Math.min(width, height) * 0.32;
    return {
      id: d.id,
      x: width / 2 + r * Math.cos(angle),
      y: height / 2 + r * Math.sin(angle),
      color: STATUS_COLOR[d.status] ?? "#3b82f6",
      label: d.title,
      status: d.status,
    };
  });

  const edges: Edge[] = [];
  for (let i = 0; i < nodes.length - 1; i++) {
    if (hashStr(nodes[i].id + nodes[i + 1].id) % 3 !== 0) {
      edges.push({ source: nodes[i].id, target: nodes[i + 1].id });
    }
  }
  if (nodes.length > 2) {
    edges.push({ source: nodes[0].id, target: nodes[Math.floor(nodes.length / 2)].id });
  }

  return { nodes, edges };
}

interface MiniGraphPreviewProps {
  decisions: Decision[];
}

export function MiniGraphPreview({ decisions }: MiniGraphPreviewProps) {
  const router = useRouter();
  const width = 280;
  const height = 200;

  if (!decisions || decisions.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-xs text-muted-foreground">
        No graph data yet
      </div>
    );
  }

  const { nodes, edges } = buildGraph(decisions, width, height);
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="cursor-pointer"
      onClick={() => router.push("/dependency-map")}
      title="Click to open Dependency Map"
    >
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
        {/* Edges */}
        {edges.map((e, i) => {
          const s = nodeMap.get(e.source);
          const t = nodeMap.get(e.target);
          if (!s || !t) return null;
          return (
            <line
              key={i}
              x1={s.x} y1={s.y}
              x2={t.x} y2={t.y}
              stroke="hsl(var(--border))"
              strokeWidth="1"
              opacity="0.6"
            />
          );
        })}

        {/* Center node */}
        <motion.circle
          cx={width / 2}
          cy={height / 2}
          r={7}
          fill="hsl(var(--primary))"
          fillOpacity={0.3}
          stroke="hsl(var(--primary))"
          strokeWidth={1.5}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.3 }}
        />
        <text
          x={width / 2}
          y={height / 2 + 14}
          textAnchor="middle"
          fontSize="8"
          fill="hsl(var(--muted-foreground))"
          fontFamily="var(--font-plus-jakarta, sans-serif)"
        >
          Twin
        </text>

        {/* Decision nodes */}
        {nodes.map((n, i) => (
          <motion.g
            key={n.id}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.15 + i * 0.04, duration: 0.25 }}
          >
            <circle
              cx={n.x}
              cy={n.y}
              r={4.5}
              fill={n.color}
              fillOpacity={0.7}
              stroke={n.color}
              strokeWidth={1}
            />
          </motion.g>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-2 flex-wrap">
        {Object.entries(STATUS_COLOR).map(([status, color]) => (
          <span key={status} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ background: color }} />
            <span className="text-xs text-muted-foreground capitalize">{status}</span>
          </span>
        ))}
      </div>
    </motion.div>
  );
}
