"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ScrollText, Zap, CheckCircle2, AlertTriangle, Clock } from "lucide-react";
import { useActionHistory } from "@/lib/hooks";
import { TimelineRow } from "@/components/shared/TimelineRow";
import { FilterBar } from "@/components/shared/FilterBar";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { PolicyPathViewer } from "@/components/shared/PolicyPathViewer";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { PermissionBadge } from "@/components/shared/PermissionBadge";
import { MetricCard } from "@/components/shared/MetricCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { useInspector } from "@/components/providers";
import type { AgentAction } from "@/lib/types";

const STATUS_OPTIONS = [
  { value: "allowed", label: "Allowed" },
  { value: "blocked", label: "Blocked" },
  { value: "denied", label: "Denied" },
  { value: "pending", label: "Pending" },
  { value: "escalated", label: "Escalated" },
];

function ActionDetail({ action }: { action: AgentAction }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <StatusBadge status={action.status} />
        <PermissionBadge allowed={action.status === "allowed"} />
      </div>
      <div className="space-y-2">
        {[
          ["Action Type", action.action_type],
          ["Initiated by", action.initiated_by],
          ["Agent", action.executed_by_agent],
          ["Timestamp", new Date(action.timestamp).toLocaleString()],
          ["ID", action.id],
        ].map(([k, v]) => (
          <div key={k} className="flex flex-col gap-0.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{k}</span>
            <span className="text-xs text-foreground font-mono bg-muted/40 rounded-md px-2 py-1">{v}</span>
          </div>
        ))}
      </div>
      <div>
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
          Policy Path
        </div>
        <PolicyPathViewer path={action.policy_path} />
      </div>
    </div>
  );
}

export default function AuditPage() {
  const { data: actions, isLoading } = useActionHistory();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const { openInspector } = useInspector();

  const actionTypes = useMemo(() => {
    if (!actions) return [];
    return [...new Set(actions.map((a) => a.action_type))].map((t) => ({ value: t, label: t }));
  }, [actions]);

  const filtered = useMemo(() => {
    if (!actions) return [];
    return actions.filter((a) => {
      const matchesSearch =
        !search ||
        a.action_type.toLowerCase().includes(search.toLowerCase()) ||
        a.initiated_by.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "all" || a.status === statusFilter;
      const matchesType = typeFilter === "all" || a.action_type === typeFilter;
      return matchesSearch && matchesStatus && matchesType;
    });
  }, [actions, search, statusFilter, typeFilter]);

  const stats = useMemo(() => {
    if (!actions) return null;
    return {
      total: actions.length,
      allowed: actions.filter((a) => a.status === "allowed").length,
      blocked: actions.filter((a) => a.status === "blocked" || a.status === "denied").length,
      pending: actions.filter((a) => a.status === "pending").length,
    };
  }, [actions]);

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <PageHeader icon={ScrollText} title="Audit Log" subtitle="Full replay of agent actions with policy traces" />

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Total" value={stats.total} icon={ScrollText} accent="default" size="sm" />
          <MetricCard label="Allowed" value={stats.allowed} icon={CheckCircle2} accent="emerald" size="sm" />
          <MetricCard label="Blocked" value={stats.blocked} icon={AlertTriangle} accent="crimson" size="sm" />
          <MetricCard label="Pending" value={stats.pending} icon={Clock} accent="amber" size="sm" />
        </div>
      )}

      <FilterBar
        search={{ value: search, onChange: setSearch, placeholder: "Search actions…" }}
        filters={[
          {
            key: "status",
            label: "Status",
            options: STATUS_OPTIONS,
            value: statusFilter,
            onChange: setStatusFilter,
          },
          {
            key: "type",
            label: "Type",
            options: actionTypes,
            value: typeFilter,
            onChange: setTypeFilter,
          },
        ]}
      />

      {isLoading ? (
        <LoadingState rows={5} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={actions?.length === 0 ? "No audit records" : "No results match your filters"}
          description={
            actions?.length === 0
              ? "Agent actions will appear here once they are executed."
              : "Try adjusting your filters."
          }
          action={
            actions && actions.length > 0 && (search || statusFilter !== "all" || typeFilter !== "all") ? (
              <button
                onClick={() => { setSearch(""); setStatusFilter("all"); setTypeFilter("all"); }}
                className="text-xs text-primary hover:underline"
              >
                Clear filters
              </button>
            ) : undefined
          }
        />
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
        >
          {filtered.map((action, i) => (
            <TimelineRow
              key={action.id}
              timestamp={new Date(action.timestamp).toLocaleString()}
              icon={Zap}
              title={action.action_type}
              subtitle={`${action.initiated_by} via ${action.executed_by_agent}`}
              status={action.status}
              isLast={i === filtered.length - 1}
              onClick={() => openInspector(action.action_type, <ActionDetail action={action} />)}
            />
          ))}
        </motion.div>
      )}
    </div>
  );
}
