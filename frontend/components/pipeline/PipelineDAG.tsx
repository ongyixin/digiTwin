"use client";

import { StageCard } from "./StageCard";
import type { StageInfo, JobStatus } from "@/lib/types";

interface PipelineDAGProps {
  stages: StageInfo[];
  status: JobStatus;
}

export function PipelineDAG({ stages, status }: PipelineDAGProps) {
  return (
    <div className="space-y-0">
      {stages.map((stage, i) => (
        <StageCard
          key={stage.name}
          stage={stage}
          isLast={i === stages.length - 1}
        />
      ))}
    </div>
  );
}
