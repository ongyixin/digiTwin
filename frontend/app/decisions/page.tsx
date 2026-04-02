"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useDecisions } from "@/lib/hooks";
import { EntityCard } from "@/components/shared/EntityCard";
import { FilterBar } from "@/components/shared/FilterBar";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { MetricCard } from "@/components/shared/MetricCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { ArtifactModal } from "@/components/shared/ArtifactModal";
import { GitBranch, CheckCircle2, Clock, XCircle } from "lucide-react";
import { CyclingGraphBackground } from "@/components/dashboard/GraphBackgrounds";

const STATUS_OPTIONS = [
  { value: "proposed", label: "Proposed" },
  { value: "approved", label: "Approved" },
  { value: "superseded", label: "Superseded" },
  { value: "rejected", label: "Rejected" },
];

const STATUS_TABS = [
  { label: "All", value: "all" },
  { label: "Proposed", value: "proposed" },
  { label: "Approved", value: "approved" },
  { label: "Superseded", value: "superseded" },
];

const listVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04 } },
};
const rowVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0 },
};

export default function DecisionsPage() {
  const { data: decisions, isLoading } = useDecisions();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const stats = useMemo(() => {
    if (!decisions) return null;
    return {
      total: decisions.length,
      proposed: decisions.filter((d) => d.status === "proposed").length,
      approved: decisions.filter((d) => d.status === "approved").length,
      rejected: decisions.filter((d) => d.status === "rejected").length,
    };
  }, [decisions]);

  const filtered = useMemo(() => {
    if (!decisions) return [];
    return decisions.filter((d) => {
      const matchesSearch =
        !search ||
        d.title.toLowerCase().includes(search.toLowerCase()) ||
        d.summary.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "all" || d.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [decisions, search, statusFilter]);

  return (
    <div className="relative">
      <CyclingGraphBackground opacity={0.3} />
      <div className="relative z-10 p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <PageHeader
        icon={GitBranch}
        title="Decisions"
        subtitle="All decisions extracted from your meetings and documents"
        actions={<ArtifactModal />}
      />

      {/* Stat bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Total" value={stats.total} icon={GitBranch} accent="blue" size="sm" />
          <MetricCard label="Proposed" value={stats.proposed} icon={Clock} accent="amber" size="sm" />
          <MetricCard label="Approved" value={stats.approved} icon={CheckCircle2} accent="emerald" size="sm" />
          <MetricCard label="Rejected" value={stats.rejected} icon={XCircle} accent="crimson" size="sm" />
        </div>
      )}

      {/* Status tabs */}
      <div className="flex items-center gap-1 border-b border-border">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStatusFilter(tab.value)}
            className={[
              "px-3 py-2 text-xs font-medium transition-colors relative",
              statusFilter === tab.value
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {tab.label}
            {statusFilter === tab.value && (
              <motion.div
                layoutId="decisions-tab-indicator"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full"
              />
            )}
          </button>
        ))}
      </div>

      <FilterBar
        search={{ value: search, onChange: setSearch, placeholder: "Search decisions…" }}
        filters={[
          {
            key: "status",
            label: "Status",
            options: STATUS_OPTIONS,
            value: statusFilter,
            onChange: setStatusFilter,
          },
        ]}
      />

      {isLoading ? (
        <LoadingState rows={5} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={decisions?.length === 0 ? "No decisions yet" : "No results match your filters"}
          description={
            decisions?.length === 0
              ? "Ingest a meeting transcript to start extracting decisions."
              : "Try adjusting your search or filter criteria."
          }
          action={
            decisions?.length === 0 ? (
              <ArtifactModal />
            ) : (
              <button
                onClick={() => { setSearch(""); setStatusFilter("all"); }}
                className="text-xs text-primary hover:underline"
              >
                Clear filters
              </button>
            )
          }
        />
      ) : (
        <motion.div
          className="space-y-2"
          initial="hidden"
          animate="visible"
          variants={listVariants}
        >
          {filtered.map((d) => (
            <motion.div key={d.id} variants={rowVariants}>
              <EntityCard
                id={d.id}
                title={d.title}
                summary={d.summary}
                status={d.status}
                confidence={d.confidence}
                ownerName={d.owner_name}
                meetingTitle={d.meeting_title}
                href={`/decisions/${d.id}`}
              />
            </motion.div>
          ))}
        </motion.div>
      )}
      </div>
    </div>
  );
}
