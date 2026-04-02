"use client";

import { useEffect, useRef } from "react";
import Graph from "graphology";
import { Sigma } from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";
import { GRAPH_NODE_COLORS } from "@/lib/constants";
import type { GraphNode, GraphEdge } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SigmaGraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId?: string | null;
  activeTypes?: Set<string>;
  onSelect?: (node: GraphNode) => void;
  className?: string;
}

export function SigmaGraphViewer({
  nodes,
  edges,
  selectedId,
  activeTypes,
  onSelect,
  className,
}: SigmaGraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);
  const nodeMapRef = useRef<Map<string, GraphNode>>(new Map());

  useEffect(() => {
    if (!containerRef.current) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const graph = new (Graph as any)({ multi: false, allowSelfLoops: false }) as any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    graphRef.current = graph as any;
    nodeMapRef.current = new Map();

    const visibleNodes = activeTypes
      ? nodes.filter((n) => activeTypes.has(n.label))
      : nodes;

    const visibleIds = new Set(visibleNodes.map((n) => n.id));

    visibleNodes.forEach((n, i) => {
      const color = GRAPH_NODE_COLORS[n.label] || "#94a3b8";
      const angle = (i / visibleNodes.length) * 2 * Math.PI;
      const r = Math.max(3, visibleNodes.length * 0.4);
      if (!graph.hasNode(n.id)) {
        const nodeSize =
          n.label === "Decision" ? 10
          : n.label === "ResolutionCase" ? 9
          : n.label === "Meeting" ? 8
          : n.label === "ProposedAction" ? 7
          : 6;
        graph.addNode(n.id, {
          x: Math.cos(angle) * r,
          y: Math.sin(angle) * r,
          label: String(
            n.properties.title || n.properties.text || n.properties.name || n.id
          ).substring(0, 32),
          size: nodeSize,
          color,
          type: "circle",
        });
        nodeMapRef.current.set(n.id, n);
      }
    });

    edges.forEach((e) => {
      if (!visibleIds.has(e.source) || !visibleIds.has(e.target)) return;
      const edgeId = `e-${e.source}-${e.target}`;
      if (!graph.hasEdge(edgeId)) {
        try {
          graph.addEdgeWithKey(edgeId, e.source, e.target, {
            label: e.type,
            color: "#4b5563",
            size: 1.5,
          });
        } catch (_) {
          // skip duplicate edges
        }
      }
    });

    // Run ForceAtlas2 layout
    if (graph.order > 0) {
      forceAtlas2.assign(graph, {
        iterations: 150,
        settings: {
          gravity: 1.2,
          scalingRatio: 5,
          slowDown: 3,
          barnesHutOptimize: graph.order > 30,
        },
      });
    }

    const sigma = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: false,
      defaultNodeColor: "#94a3b8",
      defaultEdgeColor: "#4b5563",
      labelFont: "var(--font-plus-jakarta, system-ui)",
      labelSize: 11,
      labelWeight: "500",
      labelColor: { color: "#e2e8f0" },
      nodeProgramClasses: {},
    });
    sigmaRef.current = sigma;

    sigma.on("clickNode", ({ node }) => {
      const graphNode = nodeMapRef.current.get(node);
      if (graphNode && onSelect) {
        onSelect(graphNode);
      }
    });

    return () => {
      sigma.kill();
      sigmaRef.current = null;
    };
  }, [nodes, edges, activeTypes]);

  // Highlight selected node
  useEffect(() => {
    const sigma = sigmaRef.current;
    const graph = graphRef.current;
    if (!sigma || !graph) return;

    graph.forEachNode((id: string) => {
      const original = GRAPH_NODE_COLORS[
        nodeMapRef.current.get(id)?.label || ""
      ] || "#94a3b8";
      const nodeData = nodeMapRef.current.get(id);
      const baseSize =
        nodeData?.label === "Decision" ? 10
        : nodeData?.label === "ResolutionCase" ? 9
        : nodeData?.label === "Meeting" ? 8
        : nodeData?.label === "ProposedAction" ? 7
        : 6;
      graph.setNodeAttribute(id, "color", id === selectedId ? "#60a5fa" : original);
      graph.setNodeAttribute(id, "size", id === selectedId ? 14 : baseSize);
    });
    sigma.refresh();
  }, [selectedId]);

  return (
    <div
      ref={containerRef}
      className={cn("w-full h-full", className)}
      style={{ minHeight: 400 }}
    />
  );
}
