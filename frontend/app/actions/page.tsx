"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, Clock, History } from "lucide-react";
import { api } from "@/lib/api";
import { useActionHistory } from "@/lib/hooks";
import { UserSelector } from "@/components/shared/UserSelector";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { PolicyPathViewer } from "@/components/shared/PolicyPathViewer";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { TimelineRow } from "@/components/shared/TimelineRow";
import { PageHeader } from "@/components/shared/PageHeader";
import { OwnerChip } from "@/components/shared/OwnerChip";
import { PulseIndicator } from "@/components/shared/PulseIndicator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { useInspector } from "@/components/providers";
import type { DraftFollowupResponse, DraftedMessage, AgentAction } from "@/lib/types";

function PolicyInspectorContent({ path, reason }: { path: string[]; reason?: string }) {
  return (
    <div className="space-y-3">
      {reason && <p className="text-xs text-muted-foreground">{reason}</p>}
      <PolicyPathViewer path={path} />
    </div>
  );
}

function ActionInspectorContent({ action }: { action: AgentAction }) {
  return (
    <div className="space-y-4">
      <StatusBadge status={action.status} />
      <div className="space-y-2">
        {[
          ["Type", action.action_type],
          ["Initiated by", action.initiated_by],
          ["Agent", action.executed_by_agent],
          ["Status", action.status],
          ["Timestamp", new Date(action.timestamp).toLocaleString()],
        ].map(([k, v]) => (
          <div key={k} className="flex flex-col gap-0.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{k}</span>
            <span className="text-xs text-foreground font-mono bg-muted/40 rounded-md px-2 py-1">{v}</span>
          </div>
        ))}
      </div>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
          Policy Path
        </div>
        <PolicyPathViewer path={action.policy_path} />
      </div>
    </div>
  );
}

export default function ActionsPage() {
  const [userId, setUserId] = useState("alex");
  const [result, setResult] = useState<DraftFollowupResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { data: historyData, isLoading: historyLoading } = useActionHistory();
  const { openInspector } = useInspector();

  async function run() {
    setLoading(true);
    setError("");
    try {
      const res = await api.draftFollowups(userId);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  const allowed = result?.drafted.filter((d) => !d.blocked) ?? [];
  const blocked = result?.drafted.filter((d) => d.blocked) ?? [];

  function openPolicyInspector(msg: DraftedMessage) {
    openInspector(
      `Policy: ${msg.target_person_name}`,
      <PolicyInspectorContent path={msg.policy_path} reason={msg.block_reason} />
    );
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <PageHeader icon={Zap} title="Action Center" subtitle="Draft policy-enforced follow-up messages for pending approvals" />

      {/* Command console card */}
      <div
        className="border border-border rounded-xl p-5 space-y-4 relative overflow-hidden"
        style={{ background: "hsl(var(--surface-2, var(--card)))" }}
      >
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-primary/50 to-transparent" />
        <div>
          <h2 className="text-sm font-semibold text-foreground">Draft Follow-ups</h2>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            digiTwin finds pending approvals, checks your permissions, and drafts messages only for
            actions you are allowed to take.
          </p>
        </div>
        <div className="flex gap-3 items-end flex-wrap">
          <UserSelector value={userId} onChange={setUserId} />
          <Button onClick={run} disabled={loading} size="sm" className="gap-2 shadow-glow-sm">
            <Zap className="w-3.5 h-3.5" />
            {loading ? "Running…" : "Draft Follow-ups"}
          </Button>
        </div>
        {error && (
          <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/25 rounded-lg px-3 py-2.5">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <Tabs defaultValue="drafts">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <TabsList className="bg-[hsl(var(--surface-0,var(--background)))]">
              <TabsTrigger value="drafts" className="gap-1.5 text-xs data-[state=active]:border-b-2 data-[state=active]:border-primary">
                Drafts
                <span className="bg-emerald-500/15 text-emerald-400 text-xs font-semibold px-1.5 py-0.5 rounded">
                  {allowed.length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="blocked" className="gap-1.5 text-xs">
                Blocked
                <span className="bg-red-500/15 text-red-400 text-xs font-semibold px-1.5 py-0.5 rounded">
                  {blocked.length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="history" className="text-xs">History</TabsTrigger>
            </TabsList>
            <span className="text-xs font-mono text-muted-foreground">ID: {result.agent_action_id}</span>
          </div>

          <AnimatePresence mode="wait">
            <TabsContent value="drafts">
              {allowed.length === 0 ? (
                <EmptyState icon={Clock} title="No allowed actions" description="No pending approvals found for this user." />
              ) : (
                <div className="space-y-3">
                  {allowed.map((msg, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className="bg-card border border-emerald-500/20 rounded-xl p-4 space-y-3 relative overflow-hidden"
                    >
                      <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-emerald-500 rounded-r-full" />
                      <div className="flex items-center justify-between pl-3">
                        <div className="flex items-center gap-2">
                          <OwnerChip name={msg.target_person_name} />
                        </div>
                        <StatusBadge status="allowed" />
                      </div>
                      <div className="text-xs text-muted-foreground pl-3">
                        <span className="font-medium text-foreground/80">Subject: </span>{msg.subject}
                      </div>
                      <div className="text-sm text-foreground bg-muted/40 border border-border rounded-lg p-3 whitespace-pre-wrap font-mono leading-relaxed">
                        {msg.body}
                      </div>
                      <div className="pl-3">
                        <div className="text-xs text-muted-foreground mb-1">Policy path</div>
                        <button onClick={() => openPolicyInspector(msg)} className="text-left hover:opacity-80 transition-opacity">
                          <PolicyPathViewer path={msg.policy_path} compact />
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="blocked">
              {blocked.length === 0 ? (
                <EmptyState icon={Zap} title="No blocked actions" description="All actions were allowed." />
              ) : (
                <div className="space-y-3">
                  {blocked.map((msg, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className="bg-card border border-red-500/20 rounded-xl p-4 space-y-3 relative overflow-hidden"
                    >
                      <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-red-500 rounded-r-full" />
                      <div className="flex items-center justify-between pl-3">
                        <div className="flex items-center gap-2">
                          <PulseIndicator color="crimson" pulse />
                          <OwnerChip name={msg.target_person_name} />
                        </div>
                        <StatusBadge status="blocked" />
                      </div>
                      <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3 ml-3">
                        {msg.block_reason}
                      </div>
                      <div className="pl-3">
                        <div className="text-xs text-muted-foreground mb-1">Policy path</div>
                        <button onClick={() => openPolicyInspector(msg)} className="text-left hover:opacity-80 transition-opacity">
                          <PolicyPathViewer path={msg.policy_path} compact />
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="history">
              <ActionHistory data={historyData ?? []} isLoading={historyLoading} />
            </TabsContent>
          </AnimatePresence>
        </Tabs>
      )}

      {/* History when no result yet */}
      {!result && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <History className="w-4 h-4 text-muted-foreground" /> Action History
          </h2>
          <ActionHistory data={historyData ?? []} isLoading={historyLoading} />
        </div>
      )}
    </div>
  );
}

function ActionHistory({ data, isLoading }: { data: AgentAction[]; isLoading: boolean }) {
  const { openInspector } = useInspector();
  if (isLoading) return <LoadingState rows={3} />;
  if (data.length === 0) {
    return <EmptyState icon={History} title="No action history" description="Actions will appear here once the agent runs." />;
  }
  return (
    <div className="space-y-1">
      {data.map((action, i) => (
        <TimelineRow
          key={action.id}
          timestamp={new Date(action.timestamp).toLocaleString()}
          title={action.action_type}
          subtitle={`${action.initiated_by} via ${action.executed_by_agent}`}
          status={action.status}
          isLast={i === data.length - 1}
          onClick={() => openInspector(action.action_type, <ActionInspectorContent action={action} />)}
        />
      ))}
    </div>
  );
}
