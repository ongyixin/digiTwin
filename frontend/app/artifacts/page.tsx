"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { ArtifactModal } from "@/components/shared/ArtifactModal";
import { ArtifactTypeBadge, ARTIFACT_TYPE_CONFIG } from "@/components/shared/ArtifactTypeBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import type { ArtifactRecord, ArtifactType } from "@/lib/types";
import { Database, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { CyclingGraphBackground } from "@/components/dashboard/GraphBackgrounds";

const SENSITIVITY_COLOR: Record<string, string> = {
  public: "text-emerald-400",
  internal: "text-blue-400",
  confidential: "text-amber-400",
  restricted: "text-red-400",
};

const ALL_TYPES = Object.keys(ARTIFACT_TYPE_CONFIG) as ArtifactType[];

const rowVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0 },
};

export default function ArtifactsPage() {
  const router = useRouter();
  const [typeFilter, setTypeFilter] = useState<ArtifactType | "">("");

  const { data: artifacts = [], isLoading, refetch } = useQuery({
    queryKey: ["artifacts", typeFilter],
    queryFn: () => api.listArtifacts("default", typeFilter || undefined),
    refetchInterval: 10000,
  });

  return (
    <div className="relative">
      <CyclingGraphBackground opacity={0.3} />
      <div className="relative z-10 p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <PageHeader
        icon={Database}
        title="Artifacts"
        subtitle={`${artifacts.length} artifact${artifacts.length !== 1 ? "s" : ""} ingested`}
        actions={
          <>
            <Button variant="ghost" size="sm" onClick={() => refetch()} className="gap-1.5 text-xs">
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </Button>
            <ArtifactModal />
          </>
        }
      />

      {/* Type filter pills */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setTypeFilter("")}
          className={cn(
            "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all",
            typeFilter === ""
              ? "bg-primary/15 text-primary border-primary/40 shadow-glow-sm"
              : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground"
          )}
        >
          All
        </button>
        {ALL_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(typeFilter === t ? "" : t)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition-all",
              typeFilter === t
                ? "bg-primary/15 text-primary border-primary/40 shadow-glow-sm"
                : "border-border text-muted-foreground hover:border-primary/30 hover:text-foreground"
            )}
          >
            <ArtifactTypeBadge type={t} showLabel={false} />
            {ARTIFACT_TYPE_CONFIG[t]?.label}
          </button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <LoadingState rows={5} />
      ) : artifacts.length === 0 ? (
        <EmptyState
          title="No artifacts yet"
          description="Add a transcript, document, recording, or GitHub repo to get started"
          action={<ArtifactModal />}
        />
      ) : (
        <motion.div
          className="space-y-2"
          initial="hidden"
          animate="visible"
          variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.04 } } }}
        >
          {artifacts.map((artifact) => (
            <motion.div key={artifact.id} variants={rowVariants}>
              <ArtifactRow
                artifact={artifact}
                onClick={() => router.push("/decisions")}
              />
            </motion.div>
          ))}
        </motion.div>
      )}
      </div>
    </div>
  );
}

function ArtifactRow({ artifact, onClick }: { artifact: ArtifactRecord; onClick: () => void }) {
  return (
    <motion.div
      whileHover={{ y: -1 }}
      transition={{ duration: 0.12 }}
      className="flex items-center gap-4 px-4 py-3.5 rounded-xl border border-border bg-card hover:border-primary/30 cursor-pointer transition-colors group relative overflow-hidden"
      onClick={onClick}
    >
      {/* Hover accent bar */}
      <div className="absolute left-0 top-3 bottom-3 w-0 group-hover:w-0.5 bg-primary rounded-r-full transition-all duration-150" />

      <ArtifactTypeBadge type={artifact.type} size="md" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
          {artifact.title}
        </p>
        <p className="text-xs text-muted-foreground font-mono mt-0.5">
          {artifact.source_type} · {new Date(artifact.ingested_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
        </p>
      </div>

      <StatusBadge status={artifact.status} />

      <span className={cn("text-xs capitalize font-medium", SENSITIVITY_COLOR[artifact.sensitivity] ?? "text-muted-foreground")}>
        {artifact.sensitivity}
      </span>

      <span className="text-xs text-muted-foreground font-mono w-8 text-right shrink-0">
        v{artifact.version_count || 1}
      </span>
    </motion.div>
  );
}
