"use client";

import { useEffect, useRef, useState } from "react";
import { GRAPH_NODE_COLORS } from "@/lib/constants";
import type { GraphNode, GraphEdge } from "@/lib/types";
import { cn } from "@/lib/utils";

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId?: string | null;
  activeTypes?: Set<string>;
  onSelect?: (node: GraphNode) => void;
  className?: string;
}

export function GraphViewer({
  nodes,
  edges,
  selectedId,
  activeTypes,
  onSelect,
  className,
}: GraphViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [dims, setDims] = useState({ w: 600, h: 400 });

  // Responsive dims
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const e = entries[0];
      setDims({ w: e.contentRect.width, h: e.contentRect.height });
    });
    ro.observe(el);
    setDims({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  // Force-directed layout
  useEffect(() => {
    if (!nodes.length) return;
    const { w, h } = dims;
    const pos: Record<string, { x: number; y: number; vx: number; vy: number }> = {};

    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI;
      pos[n.id] = {
        x: w / 2 + Math.cos(angle) * (Math.min(w, h) * 0.28),
        y: h / 2 + Math.sin(angle) * (Math.min(w, h) * 0.28),
        vx: 0,
        vy: 0,
      };
    });

    for (let iter = 0; iter < 80; iter++) {
      for (const a of nodes) {
        for (const b of nodes) {
          if (a.id === b.id) continue;
          const dx = pos[a.id].x - pos[b.id].x;
          const dy = pos[a.id].y - pos[b.id].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 4000 / (dist * dist);
          pos[a.id].vx += (dx / dist) * force;
          pos[a.id].vy += (dy / dist) * force;
        }
      }
      for (const e of edges) {
        const s = pos[e.source];
        const t = pos[e.target];
        if (!s || !t) continue;
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist / 80;
        s.vx += (dx / dist) * force;
        s.vy += (dy / dist) * force;
        t.vx -= (dx / dist) * force;
        t.vy -= (dy / dist) * force;
      }
      for (const n of nodes) {
        pos[n.id].vx += (w / 2 - pos[n.id].x) * 0.01;
        pos[n.id].vy += (h / 2 - pos[n.id].y) * 0.01;
        pos[n.id].x = Math.max(24, Math.min(w - 24, pos[n.id].x + pos[n.id].vx * 0.1));
        pos[n.id].y = Math.max(24, Math.min(h - 24, pos[n.id].y + pos[n.id].vy * 0.1));
        pos[n.id].vx *= 0.8;
        pos[n.id].vy *= 0.8;
      }
    }

    setPositions(Object.fromEntries(Object.entries(pos).map(([k, v]) => [k, { x: v.x, y: v.y }])));
  }, [nodes, edges, dims]);

  // Draw
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !Object.keys(positions).length) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = dims.w * dpr;
    canvas.height = dims.h * dpr;
    canvas.style.width = dims.w + "px";
    canvas.style.height = dims.h + "px";
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, dims.w, dims.h);

    const filteredNodes = activeTypes
      ? nodes.filter((n) => activeTypes.has(n.label))
      : nodes;
    const filteredIds = new Set(filteredNodes.map((n) => n.id));

    // Neighbor highlighting for selected node
    const neighborIds = new Set<string>();
    if (selectedId) {
      for (const e of edges) {
        if (e.source === selectedId) neighborIds.add(e.target);
        if (e.target === selectedId) neighborIds.add(e.source);
      }
    }

    // Edges
    for (const e of edges) {
      if (!filteredIds.has(e.source) || !filteredIds.has(e.target)) continue;
      const s = positions[e.source];
      const t = positions[e.target];
      if (!s || !t) continue;

      const dimmed = selectedId && e.source !== selectedId && e.target !== selectedId;
      ctx.strokeStyle = dimmed ? "#1e2230" : "#3a4260";
      ctx.lineWidth = 1;
      ctx.globalAlpha = dimmed ? 0.3 : 0.7;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Nodes
    for (const n of filteredNodes) {
      const pos = positions[n.id];
      if (!pos) continue;
      const color = GRAPH_NODE_COLORS[n.label] || GRAPH_NODE_COLORS.Node;
      const isSelected = n.id === selectedId;
      const isNeighbor = neighborIds.has(n.id);
      const dimmed = selectedId && !isSelected && !isNeighbor;

      ctx.globalAlpha = dimmed ? 0.25 : 1;

      if (isSelected) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 16, 0, 2 * Math.PI);
        ctx.fillStyle = color + "33";
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(pos.x, pos.y, isSelected ? 9 : 7, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = isSelected ? "#60a5fa" : color + "55";
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.stroke();

      ctx.fillStyle = dimmed ? "#3a4050" : "#b8bfd0";
      ctx.font = `${isSelected ? "600 " : ""}10px var(--font-plus-jakarta, system-ui), sans-serif`;
      ctx.textAlign = "center";
      const label = String(
        n.properties.title || n.properties.text || n.properties.name || n.id
      ).substring(0, 22);
      ctx.fillText(label, pos.x, pos.y + 20);

      ctx.globalAlpha = 1;
    }
  }, [positions, nodes, edges, selectedId, activeTypes, dims]);

  function handleClick(e: React.MouseEvent<HTMLCanvasElement>) {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect || !onSelect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const filteredNodes = activeTypes ? nodes.filter((n) => activeTypes.has(n.label)) : nodes;
    for (const n of filteredNodes) {
      const pos = positions[n.id];
      if (!pos) continue;
      if (Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2) < 14) {
        onSelect(n);
        break;
      }
    }
  }

  return (
    <div ref={containerRef} className={cn("w-full h-full", className)}>
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        className="cursor-pointer"
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
