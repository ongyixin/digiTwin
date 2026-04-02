"use client";

import { Clock } from "lucide-react";
import { useTimeline } from "@/lib/hooks";
import { TimelineView } from "@/components/timeline/TimelineView";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { PageHeader } from "@/components/shared/PageHeader";
import { ArtifactModal } from "@/components/shared/ArtifactModal";

export default function TimelinePage() {
  const { data: decisions, isLoading } = useTimeline();

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-3xl mx-auto">
      <PageHeader
        icon={Clock}
        title="Decision Timeline"
        subtitle="Scrub through history to see how the twin evolved over time"
      />

      {isLoading ? (
        <LoadingState rows={5} />
      ) : !decisions || decisions.length === 0 ? (
        <EmptyState
          title="No decisions yet"
          description="Ingest a meeting transcript to populate the timeline."
          action={<ArtifactModal />}
        />
      ) : (
        <TimelineView decisions={decisions} />
      )}
    </div>
  );
}
