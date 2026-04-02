"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Activity, Zap } from "lucide-react";
import { ResolveButton } from "@/components/shared/ResolveButton";
import { useDecisionLineage, useDecisionImpact } from "@/lib/hooks";
import { GraphViewer } from "@/components/graph/GraphViewer";
import { GraphLegend } from "@/components/graph/GraphLegend";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { PolicyPathViewer } from "@/components/shared/PolicyPathViewer";
import { LoadingState } from "@/components/shared/LoadingState";
import { useInspector } from "@/components/providers";
import { GRAPH_NODE_COLORS } from "@/lib/constants";
import type { GraphNode } from "@/lib/types";
import { CyclingGraphBackground } from "@/components/dashboard/GraphBackgrounds";

const ALL_TYPES = new Set(Object.keys(GRAPH_NODE_COLORS));

function ProvenanceBadge({ chunk, speaker }: { chunk?: number; speaker?: string }) {
  if (chunk === undefined && !speaker) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs bg-muted/60 text-muted-foreground px-2 py-0.5 rounded-full font-mono">
      {speaker && <span title="Speaker">{speaker}</span>}
      {chunk !== undefined && <span title="Chunk index">chunk {chunk}</span>}
    </span>
  );
}

function DecisionHeader({ node, id }: { node: GraphNode; id: string }) {
  const p = node.properties as {
    title?: string; status?: string; confidence?: number;
    summary?: string; source_excerpt?: string; owner_name?: string;
    meeting_title?: string; created_at?: string;
    provenance_chunk?: number; provenance_speaker?: string;
  };
  return (
    <div className="bg-card border border-border rounded-xl p-5 space-y-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <h1 className="text-lg font-bold text-foreground">{p.title || id}</h1>
        <div className="flex items-center gap-2">
          <StatusBadge status={p.status || "unknown"} />
          <span className="text-xs text-muted-foreground">
            {Math.round((p.confidence || 0) * 100)}% confidence
          </span>
        </div>
      </div>
      {p.summary && (
        <div className="flex items-start gap-2">
          <p className="text-sm text-muted-foreground flex-1">{p.summary}</p>
          <ProvenanceBadge chunk={p.provenance_chunk} speaker={p.provenance_speaker} />
        </div>
      )}
      {p.source_excerpt && (
        <blockquote className="border-l-2 border-primary/50 pl-3 text-sm text-muted-foreground italic">
          {p.source_excerpt}
        </blockquote>
      )}
      <div className="flex gap-4 text-xs text-muted-foreground font-mono">
        {p.owner_name && <span>Owner: {p.owner_name}</span>}
        {p.meeting_title && <span>Meeting: {p.meeting_title}</span>}
        {p.created_at && <span>{new Date(p.created_at).toLocaleDateString()}</span>}
      </div>
    </div>
  );
}

function NodeInspectorContent({ node }: { node: GraphNode }) {
  const props = Object.fromEntries(
    Object.entries(node.properties).filter(([k]) => k !== "embedding")
  );
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full shrink-0"
          style={{ background: GRAPH_NODE_COLORS[node.label] || "#94a3b8" }}
        />
        <span className="text-xs font-medium text-muted-foreground">{node.label}</span>
      </div>
      <div className="space-y-2">
        {Object.entries(props).map(([key, val]) => (
          <div key={key}>
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-0.5">
              {key}
            </div>
            <div className="text-xs text-foreground bg-muted/50 rounded p-2 font-mono break-all">
              {String(val)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ImpactPanel({ id }: { id: string }) {
  const { data: impact } = useDecisionImpact(id);
  if (!impact) return null;

  const scoreColor =
    impact.impact_score >= 60
      ? "text-red-400"
      : impact.impact_score >= 30
      ? "text-amber-400"
      : "text-emerald-400";

  return (
    <div className="bg-card border border-border rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold text-foreground">Impact &amp; Blast Radius</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="text-center">
          <div className={`text-2xl font-bold ${scoreColor}`}>
            {impact.impact_score}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">Impact Score</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-foreground">{impact.blast_radius}</div>
          <div className="text-xs text-muted-foreground mt-0.5">Blast Radius</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-foreground">{impact.blocked_tasks}</div>
          <div className="text-xs text-muted-foreground mt-0.5">Blocked Tasks</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-foreground">{impact.pending_approvals}</div>
          <div className="text-xs text-muted-foreground mt-0.5">Pending Approvals</div>
        </div>
      </div>
      {impact.central_approvers.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground font-semibold mb-1">Key Approvers</p>
          <div className="flex gap-1.5 flex-wrap">
            {impact.central_approvers.map((a) => (
              <span key={a} className="text-xs bg-muted px-2 py-0.5 rounded-full text-foreground">
                {a}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DecisionDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { data: subgraph, isLoading } = useDecisionLineage(id);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<string>>(ALL_TYPES);
  const { openInspector } = useInspector();

  function handleNodeSelect(node: GraphNode) {
    setSelectedId(node.id);
    openInspector(
      String(node.properties.title || node.properties.text || node.properties.name || node.id),
      <NodeInspectorContent node={node} />
    );
  }

  function toggleType(type: string) {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <LoadingState rows={4} />
      </div>
    );
  }

  if (!subgraph) {
    return (
      <div className="p-6 text-sm text-red-400">Decision not found.</div>
    );
  }

  const centralNode = subgraph.nodes.find((n) => n.id === id);
  const assumptions = subgraph.nodes.filter((n) => n.label === "Assumption");
  const evidence = subgraph.nodes.filter((n) => n.label === "Evidence");
  const approvals = subgraph.nodes.filter((n) => n.label === "Approval");
  const tasks = subgraph.nodes.filter((n) => n.label === "Task");

  return (
    <div className="relative">
      <CyclingGraphBackground opacity={0.3} />
      <div className="relative z-10 p-6 space-y-6 animate-fade-in">
      {/* Breadcrumb */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          <Link href="/decisions" className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="w-3.5 h-3.5" />
            Decisions
          </Link>
          <span className="text-muted-foreground/40">/</span>
          <span className="text-foreground font-medium truncate max-w-md">
            {centralNode ? String(centralNode.properties.title || id) : id}
          </span>
        </div>
        <ResolveButton targetType="decision" targetId={id} />
      </div>

      {/* Decision header */}
      {centralNode && (
        <DecisionHeader node={centralNode} id={id} />
      )}

      {/* Impact panel */}
      <ImpactPanel id={id} />

      {/* Graph + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Lineage Graph</h2>
            <span className="text-xs text-muted-foreground">{subgraph.nodes.length} nodes · {subgraph.edges.length} edges</span>
          </div>
          <GraphLegend activeTypes={activeTypes} onToggle={toggleType} />
          <div className="bg-card border border-border rounded-xl overflow-hidden" style={{ height: 400 }}>
            <GraphViewer
              nodes={subgraph.nodes}
              edges={subgraph.edges}
              selectedId={selectedId}
              activeTypes={activeTypes}
              onSelect={handleNodeSelect}
              className="w-full h-full"
            />
          </div>
        </div>

        {/* Node list */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">Nodes ({subgraph.nodes.length})</h3>
          <div className="space-y-1.5 max-h-[440px] overflow-y-auto pr-1">
            {subgraph.nodes.map((node) => (
              <button
                key={node.id}
                onClick={() => handleNodeSelect(node)}
                className={`w-full text-left bg-card border rounded-lg p-2.5 transition-colors hover:border-primary/40 ${
                  selectedId === node.id ? "border-primary/60 bg-primary/5" : "border-border"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: GRAPH_NODE_COLORS[node.label] || "#94a3b8" }}
                  />
                  <span className="text-xs font-medium text-muted-foreground">{node.label}</span>
                </div>
                <div className="text-xs text-foreground mt-0.5 truncate">
                  {String(node.properties.title || node.properties.text || node.properties.name || node.id)}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Detail panels */}
      {(assumptions.length > 0 || evidence.length > 0 || approvals.length > 0 || tasks.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Assumptions", nodes: assumptions, color: "#f59e0b" },
            { label: "Evidence", nodes: evidence, color: "#10b981" },
            { label: "Approvals", nodes: approvals, color: "#ef4444" },
            { label: "Tasks", nodes: tasks, color: "#8b5cf6" },
          ].map(
            ({ label, nodes, color }) =>
              nodes.length > 0 && (
                <div key={label} className="bg-card border border-border rounded-xl p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                    <span className="text-xs font-semibold text-foreground">
                      {label} ({nodes.length})
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {nodes.map((n) => (
                      <button
                        key={n.id}
                        onClick={() => handleNodeSelect(n)}
                        className="w-full text-left text-xs text-muted-foreground hover:text-foreground line-clamp-2 transition-colors"
                      >
                        {String(n.properties.text || n.properties.title || n.id)}
                      </button>
                    ))}
                  </div>
                </div>
              )
          )}
        </div>
      )}

      {/* Policy path info if available */}
      {Array.isArray(centralNode?.properties.policy_path) && (
        <div className="bg-card border border-border rounded-xl p-4 space-y-2">
          <div className="text-xs font-semibold text-foreground">Policy Path</div>
          <PolicyPathViewer path={centralNode!.properties.policy_path as string[]} />
        </div>
      )}
      </div>
    </div>
  );
}
