"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Network, ExternalLink, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import { SigmaGraphViewer } from "@/components/graph/SigmaGraphViewer";
import { GraphLegend } from "@/components/graph/GraphLegend";
import { FilterBar } from "@/components/shared/FilterBar";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { PulseIndicator } from "@/components/shared/PulseIndicator";
import { useInspector } from "@/components/providers";
import { GRAPH_NODE_COLORS } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import type { GraphNode, GraphEdge } from "@/lib/types";

const ALL_TYPES = new Set(Object.keys(GRAPH_NODE_COLORS));

function NodeInspectorContent({ node }: { node: GraphNode }) {
  const props = Object.fromEntries(
    Object.entries(node.properties).filter(([k]) => k !== "embedding")
  );
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full"
          style={{ background: GRAPH_NODE_COLORS[node.label] || "#94a3b8" }}
        />
        <span className="text-xs font-medium text-muted-foreground">{node.label}</span>
      </div>
      <div className="space-y-2">
        {Object.entries(props).map(([key, val]) => (
          <div key={key}>
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-0.5">{key}</div>
            <div className="text-xs text-foreground bg-muted/40 rounded-md p-2 font-mono break-all">{String(val)}</div>
          </div>
        ))}
      </div>
      {node.label === "Decision" && (
        <Link href={`/decisions/${node.id}`}>
          <Button size="sm" variant="outline" className="w-full gap-2 mt-2">
            <ExternalLink className="w-3.5 h-3.5" />
            View Decision
          </Button>
        </Link>
      )}
      {node.label === "ResolutionCase" && (
        <Link href={`/resolution/${node.id}`}>
          <Button size="sm" variant="outline" className="w-full gap-2 mt-2">
            <ExternalLink className="w-3.5 h-3.5" />
            View Resolution Case
          </Button>
        </Link>
      )}
    </div>
  );
}

export default function DependencyMapPage() {
  const [allNodes, setAllNodes] = useState<GraphNode[]>([]);
  const [allEdges, setAllEdges] = useState<GraphEdge[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [expandingId, setExpandingId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<string>>(ALL_TYPES);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const { openInspector } = useInspector();

  // Load the full graph overview on mount
  useEffect(() => {
    setIsLoading(true);
    api.getGraphOverview()
      .then((overview) => {
        setAllNodes(overview.nodes);
        setAllEdges(overview.edges);
      })
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  const expandDecision = useCallback(
    async (node: GraphNode) => {
      if (node.label !== "Decision" || expandedIds.has(node.id)) return;
      setExpandingId(node.id);
      try {
        const lineage = await api.getDecisionLineage(node.id);
        setAllNodes((prev) => {
          const existingIds = new Set(prev.map((n) => n.id));
          return [...prev, ...lineage.nodes.filter((n) => !existingIds.has(n.id))];
        });
        setAllEdges((prev) => {
          const existingEdgeKeys = new Set(prev.map((e) => `${e.source}-${e.target}`));
          return [...prev, ...lineage.edges.filter((e) => !existingEdgeKeys.has(`${e.source}-${e.target}`))];
        });
        setExpandedIds((prev) => new Set([...prev, node.id]));
      } finally {
        setExpandingId(null);
      }
    },
    [expandedIds]
  );

  function handleNodeSelect(node: GraphNode) {
    setSelectedId(node.id);
    openInspector(
      String(node.properties.title || node.properties.text || node.properties.name || node.id),
      <NodeInspectorContent node={node} />
    );
    if (node.label === "Decision") expandDecision(node);
  }

  function toggleType(type: string) {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  const visibleNodes = search
    ? allNodes.filter((n) =>
        String(n.properties.title || n.properties.text || n.properties.name || n.id)
          .toLowerCase()
          .includes(search.toLowerCase())
      )
    : allNodes;

  // Count nodes by type for legend display
  const typeCountMap = allNodes.reduce<Record<string, number>>((acc, n) => {
    acc[n.label] = (acc[n.label] || 0) + 1;
    return acc;
  }, {});

  return (
    <motion.div
      className="flex flex-col h-screen p-4 gap-3"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25 }}
    >
      {/* Compact toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-2 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
            <Network className="w-4 h-4 text-primary" />
          </div>
          <div>
            <span className="text-base font-semibold text-foreground">Dependency Map</span>
            {expandingId && (
              <span className="ml-2 text-xs text-muted-foreground animate-pulse">Expanding…</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <FilterBar
            search={{ value: search, onChange: setSearch, placeholder: "Search nodes…" }}
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActiveTypes(new Set(ALL_TYPES))}
            className="gap-1.5 text-xs"
            title="Reset filters"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      <GraphLegend activeTypes={activeTypes} onToggle={toggleType} typeCounts={typeCountMap} className="shrink-0" />

      {/* Graph canvas */}
      <div
        className="flex-1 border border-border rounded-xl overflow-hidden min-h-0 relative"
        style={{ background: "hsl(var(--surface-0, var(--background)))", boxShadow: "inset 0 1px 0 hsl(var(--border))" }}
      >
        {isLoading ? (
          <div className="p-6"><LoadingState rows={3} /></div>
        ) : allNodes.length === 0 ? (
          <EmptyState
            title="No nodes in graph"
            description="Ingest meeting transcripts and documents to populate the dependency map."
          />
        ) : (
          <SigmaGraphViewer
            nodes={visibleNodes}
            edges={allEdges}
            selectedId={selectedId}
            activeTypes={activeTypes}
            onSelect={handleNodeSelect}
            className="w-full h-full"
          />
        )}
      </div>

      {/* Footer */}
      <div className="text-xs text-muted-foreground font-mono flex items-center gap-3 shrink-0">
        <span>{allNodes.length} nodes</span>
        <span className="text-border">·</span>
        <span>{allEdges.length} edges</span>
        <span className="text-border">·</span>
        <span>{expandedIds.size} expanded</span>
        {expandingId && (
          <span className="flex items-center gap-1 text-primary">
            <PulseIndicator color="primary" size="sm" />
            Loading…
          </span>
        )}
      </div>
    </motion.div>
  );
}
