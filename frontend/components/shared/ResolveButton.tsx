"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Crosshair, ChevronDown, Eye, Lightbulb, Zap, ArrowUpRight } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import { api } from "@/lib/api";
import type { AutonomyMode } from "@/lib/types";

interface ResolveButtonProps {
  targetType: string;
  targetId: string;
  requestedBy?: string;
  className?: string;
}

const AUTONOMY_OPTIONS: { value: AutonomyMode; label: string; description: string; icon: React.ElementType }[] = [
  {
    value: "observe",
    label: "Observe",
    description: "Detect and explain only",
    icon: Eye,
  },
  {
    value: "recommend",
    label: "Recommend",
    description: "Build plan, no auto-execution",
    icon: Lightbulb,
  },
  {
    value: "auto_low_risk",
    label: "Auto low-risk",
    description: "Execute safe actions automatically",
    icon: Zap,
  },
  {
    value: "escalate_only",
    label: "Escalate only",
    description: "Route everything to review",
    icon: ArrowUpRight,
  },
];

export function ResolveButton({
  targetType,
  targetId,
  requestedBy = "alex",
  className,
}: ResolveButtonProps) {
  const [mode, setMode] = useState<AutonomyMode>("recommend");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const router = useRouter();

  async function handleResolve() {
    setLoading(true);
    try {
      const { case_id } = await api.createResolutionCase({
        target_type: targetType,
        target_id: targetId,
        requested_by: requestedBy,
        autonomy_mode: mode,
      });
      router.push(`/resolution/${case_id}`);
    } catch (err) {
      console.error("Failed to create resolution case:", err);
    } finally {
      setLoading(false);
    }
  }

  const selectedOption = AUTONOMY_OPTIONS.find((o) => o.value === mode)!;
  const SelectedIcon = selectedOption.icon;

  return (
    <div className={`flex items-center gap-0 ${className ?? ""}`}>
      <button
        onClick={handleResolve}
        disabled={loading}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-orange-500/10 text-orange-400 border border-orange-500/30 rounded-l-md hover:bg-orange-500/20 transition-colors disabled:opacity-50"
      >
        <Crosshair className="w-3.5 h-3.5" />
        {loading ? "Creating…" : "Resolve This"}
      </button>
      <Popover.Root open={open} onOpenChange={setOpen}>
        <Popover.Trigger asChild>
          <button className="flex items-center gap-0.5 px-2 py-1.5 text-xs font-medium bg-orange-500/10 text-orange-400 border border-l-0 border-orange-500/30 rounded-r-md hover:bg-orange-500/20 transition-colors">
            <SelectedIcon className="w-3 h-3" />
            <ChevronDown className="w-3 h-3" />
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="end"
            sideOffset={4}
            className="z-50 w-60 bg-card border border-border rounded-xl shadow-lg p-1 animate-in fade-in-0 zoom-in-95"
          >
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">Autonomy mode</div>
            {AUTONOMY_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              return (
                <button
                  key={opt.value}
                  onClick={() => { setMode(opt.value); setOpen(false); }}
                  className={`w-full flex items-start gap-2.5 px-2 py-2 rounded-lg text-left transition-colors hover:bg-muted/50 ${
                    mode === opt.value ? "bg-orange-500/10" : ""
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${mode === opt.value ? "text-orange-400" : "text-muted-foreground"}`} />
                  <div>
                    <div className={`text-xs font-medium ${mode === opt.value ? "text-orange-400" : "text-foreground"}`}>
                      {opt.label}
                    </div>
                    <div className="text-xs text-muted-foreground">{opt.description}</div>
                  </div>
                </button>
              );
            })}
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}
