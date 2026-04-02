"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import { ArtifactModal } from "@/components/shared/ArtifactModal";
import { ArtifactTypeBadge, ARTIFACT_TYPE_CONFIG } from "@/components/shared/ArtifactTypeBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import type { ArtifactRecord, ArtifactType } from "@/lib/types";
import { Database, RefreshCw, Archive, ArchiveRestore, Trash2 } from "lucide-react";
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

type ViewTab = "active" | "archived";

export default function ArtifactsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState<ArtifactType | "">("");
  const [view, setView] = useState<ViewTab>("active");

  // Active artifacts
  const { data: activeArtifacts = [], isLoading: activeLoading, refetch: refetchActive } = useQuery({
    queryKey: ["artifacts", typeFilter],
    queryFn: () => api.listArtifacts("default", typeFilter || undefined),
    refetchInterval: 10000,
  });

  // Archived artifacts
  const { data: archivedArtifacts = [], isLoading: archivedLoading, refetch: refetchArchived } = useQuery({
    queryKey: ["artifacts-archived", typeFilter],
    queryFn: () => api.listArchivedArtifacts("default", typeFilter || undefined),
    refetchInterval: 30000,
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => api.archiveArtifact(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      queryClient.invalidateQueries({ queryKey: ["artifacts-archived"] });
    },
  });

  const unarchiveMutation = useMutation({
    mutationFn: (id: string) => api.unarchiveArtifact(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artifacts-archived"] });
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteArtifact(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artifacts-archived"] });
    },
  });

  const artifacts = view === "active" ? activeArtifacts : archivedArtifacts;
  const isLoading = view === "active" ? activeLoading : archivedLoading;
  const refetch = view === "active" ? refetchActive : refetchArchived;

  return (
    <div className="relative">
      <CyclingGraphBackground opacity={0.3} />
      <div className="relative z-10 p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">

        <PageHeader
          icon={Database}
          title="Artifacts"
          subtitle={
            view === "active"
              ? `${activeArtifacts.length} artifact${activeArtifacts.length !== 1 ? "s" : ""} ingested`
              : `${archivedArtifacts.length} archived artifact${archivedArtifacts.length !== 1 ? "s" : ""}`
          }
          actions={
            <>
              <Button variant="ghost" size="sm" onClick={() => refetch()} className="gap-1.5 text-xs">
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </Button>
              {view === "active" && <ArtifactModal />}
            </>
          }
        />

        {/* Active / Archived tab toggle */}
        <div className="flex items-center gap-1 p-1 bg-muted/40 border border-border rounded-lg w-fit">
          <button
            onClick={() => setView("active")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
              view === "active"
                ? "bg-background text-foreground shadow-sm border border-border"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Database className="w-3.5 h-3.5" />
            Active
            {activeArtifacts.length > 0 && (
              <span className={cn(
                "ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold",
                view === "active" ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
              )}>
                {activeArtifacts.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setView("archived")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
              view === "archived"
                ? "bg-background text-foreground shadow-sm border border-border"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Archive className="w-3.5 h-3.5" />
            Archived
            {archivedArtifacts.length > 0 && (
              <span className={cn(
                "ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold",
                view === "archived" ? "bg-amber-500/15 text-amber-400" : "bg-muted text-muted-foreground"
              )}>
                {archivedArtifacts.length}
              </span>
            )}
          </button>
        </div>

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
        <AnimatePresence mode="wait">
          {isLoading ? (
            <LoadingState rows={5} />
          ) : artifacts.length === 0 ? (
            view === "active" ? (
              <EmptyState
                title="No artifacts yet"
                description="Add a transcript, document, recording, or GitHub repo to get started"
                action={<ArtifactModal />}
              />
            ) : (
              <EmptyState
                title="No archived artifacts"
                description="Artifacts you archive will appear here. They won't show up on the main dashboard."
              />
            )
          ) : (
            <motion.div
              key={view}
              className="space-y-2"
              initial="hidden"
              animate="visible"
              variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.04 } } }}
            >
              {artifacts.map((artifact) =>
                view === "active" ? (
                  <motion.div key={artifact.id} variants={rowVariants}>
                    <ActiveArtifactRow
                      artifact={artifact}
                      onClick={() => router.push("/decisions")}
                      onArchive={() => archiveMutation.mutate(artifact.id)}
                      isArchiving={archiveMutation.isPending && archiveMutation.variables === artifact.id}
                    />
                  </motion.div>
                ) : (
                  <motion.div key={artifact.id} variants={rowVariants}>
                    <ArchivedArtifactRow
                      artifact={artifact}
                      onUnarchive={() => unarchiveMutation.mutate(artifact.id)}
                      onDelete={() => deleteMutation.mutate(artifact.id)}
                      isRestoring={unarchiveMutation.isPending && unarchiveMutation.variables === artifact.id}
                      isDeleting={deleteMutation.isPending && deleteMutation.variables === artifact.id}
                    />
                  </motion.div>
                )
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ── Active artifact row ────────────────────────────────────────────────────

function ActiveArtifactRow({
  artifact,
  onClick,
  onArchive,
  isArchiving,
}: {
  artifact: ArtifactRecord;
  onClick: () => void;
  onArchive: () => void;
  isArchiving: boolean;
}) {
  return (
    <motion.div
      whileHover={{ y: -1 }}
      transition={{ duration: 0.12 }}
      className="flex items-center gap-4 px-4 py-3.5 rounded-xl border border-border bg-card hover:border-primary/30 cursor-pointer transition-colors group relative overflow-hidden"
      onClick={onClick}
    >
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

      <Button
        variant="ghost"
        size="sm"
        onClick={(e) => { e.stopPropagation(); onArchive(); }}
        disabled={isArchiving}
        className="gap-1.5 text-xs text-muted-foreground hover:text-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
        title="Archive artifact"
      >
        <Archive className="w-3.5 h-3.5" />
        Archive
      </Button>
    </motion.div>
  );
}

// ── Archived artifact row ──────────────────────────────────────────────────

function ArchivedArtifactRow({
  artifact,
  onUnarchive,
  onDelete,
  isRestoring,
  isDeleting,
}: {
  artifact: ArtifactRecord;
  onUnarchive: () => void;
  onDelete: () => void;
  isRestoring: boolean;
  isDeleting: boolean;
}) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  function handleDeleteClick(e: React.MouseEvent) {
    e.stopPropagation();
    if (confirmingDelete) {
      onDelete();
      setConfirmingDelete(false);
    } else {
      setConfirmingDelete(true);
    }
  }

  function handleCancelDelete(e: React.MouseEvent) {
    e.stopPropagation();
    setConfirmingDelete(false);
  }

  return (
    <motion.div
      whileHover={{ y: -1 }}
      transition={{ duration: 0.12 }}
      onMouseLeave={() => setConfirmingDelete(false)}
      className={cn(
        "flex items-center gap-4 px-4 py-3.5 rounded-xl border bg-card/60 opacity-80 hover:opacity-100 transition-all group relative overflow-hidden",
        confirmingDelete
          ? "border-red-500/40 bg-red-500/5"
          : "border-border hover:border-primary/20"
      )}
    >
      <div className="absolute left-0 top-3 bottom-3 w-0 group-hover:w-0.5 bg-muted-foreground/40 rounded-r-full transition-all duration-150" />

      <ArtifactTypeBadge type={artifact.type} size="md" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-muted-foreground truncate group-hover:text-foreground transition-colors">
          {artifact.title}
        </p>
        <p className="text-xs text-muted-foreground/60 font-mono mt-0.5">
          {artifact.source_type} · ingested{" "}
          {new Date(artifact.ingested_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
          {artifact.archived_at && (
            <> · archived{" "}
              {new Date(artifact.archived_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
            </>
          )}
        </p>
      </div>

      <StatusBadge status={artifact.status} />

      <span className={cn("text-xs capitalize font-medium", SENSITIVITY_COLOR[artifact.sensitivity] ?? "text-muted-foreground")}>
        {artifact.sensitivity}
      </span>

      <span className="text-xs text-muted-foreground font-mono w-8 text-right shrink-0">
        v{artifact.version_count || 1}
      </span>

      <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => { e.stopPropagation(); onUnarchive(); }}
          disabled={isRestoring || isDeleting}
          className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArchiveRestore className="w-3.5 h-3.5" />
          Restore
        </Button>

        {confirmingDelete ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDeleteClick}
              disabled={isDeleting}
              className="gap-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-red-500/30"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Confirm delete
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCancelDelete}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Cancel
            </Button>
          </>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDeleteClick}
            disabled={isDeleting || isRestoring}
            className="gap-1.5 text-xs text-muted-foreground hover:text-red-400 hover:bg-red-500/10"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete
          </Button>
        )}
      </div>
    </motion.div>
  );
}
