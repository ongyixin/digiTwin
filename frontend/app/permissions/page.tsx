"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Shield } from "lucide-react";
import { api } from "@/lib/api";
import { UserSelector } from "@/components/shared/UserSelector";
import { PermissionBadge } from "@/components/shared/PermissionBadge";
import { PolicyPathViewer } from "@/components/shared/PolicyPathViewer";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useInspector } from "@/components/providers";
import { ACTIONS, RESOURCES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { PermissionCheckResponse } from "@/lib/types";

const ROLE_COLORS: Record<string, string> = {
  admin: "text-violet-400 bg-violet-500/12 border-violet-500/25",
  manager: "text-blue-400 bg-blue-500/12 border-blue-500/25",
  viewer: "text-zinc-400 bg-zinc-500/12 border-zinc-500/25",
  approver: "text-emerald-400 bg-emerald-500/12 border-emerald-500/25",
  agent: "text-amber-400 bg-amber-500/12 border-amber-500/25",
};

const selectClass = "h-8 text-xs bg-[hsl(var(--input))] border-border focus:ring-primary/40";

export default function PermissionsPage() {
  const [userId, setUserId] = useState("alex");
  const [userPerms, setUserPerms] = useState<{
    roles: string[];
    permissions: { action: string; resource: string; scope?: string }[];
  } | null>(null);
  const [permsLoading, setPermsLoading] = useState(false);
  const [checkAction, setCheckAction] = useState("execute");
  const [checkResource, setCheckResource] = useState("send-reminder");
  const [checkResult, setCheckResult] = useState<PermissionCheckResponse | null>(null);
  const [checkLoading, setCheckLoading] = useState(false);
  const { openInspector } = useInspector();

  async function loadUserPerms() {
    setPermsLoading(true);
    try {
      const res = await api.getUserPermissions(userId);
      setUserPerms(res);
    } finally {
      setPermsLoading(false);
    }
  }

  async function runCheck() {
    setCheckLoading(true);
    try {
      const res = await api.checkPermission(userId, checkAction, checkResource);
      setCheckResult(res);
      openInspector(`${checkAction} on ${checkResource}`, <PolicyTraceContent result={res} />);
    } finally {
      setCheckLoading(false);
    }
  }

  const permsByAction: Record<string, { action: string; resource: string; scope?: string }[]> = {};
  for (const p of userPerms?.permissions ?? []) {
    if (!permsByAction[p.action]) permsByAction[p.action] = [];
    permsByAction[p.action].push(p);
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <PageHeader icon={Shield} title="Permission Inspector" subtitle="Inspect user roles and check permissions against the policy graph" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Permissions Panel */}
        <div
          className="border border-border rounded-xl p-5 space-y-4"
          style={{ background: "hsl(var(--surface-1, var(--card)))" }}
        >
          <SectionHeader title="User Permissions" />
          <div className="flex gap-2 items-end flex-wrap">
            <UserSelector value={userId} onChange={setUserId} label="User" />
            <Button onClick={loadUserPerms} disabled={permsLoading} size="sm" variant="secondary">
              {permsLoading ? "Loading…" : "Load"}
            </Button>
          </div>

          {permsLoading ? (
            <LoadingState rows={2} />
          ) : userPerms ? (
            <div className="space-y-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground/70 mb-2">
                  Roles
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {userPerms.roles.map((r) => (
                    <span
                      key={r}
                      className={cn(
                        "text-xs px-2.5 py-1 rounded-lg border font-medium",
                        ROLE_COLORS[r.toLowerCase()] ?? "text-zinc-400 bg-zinc-500/12 border-zinc-500/25"
                      )}
                    >
                      {r}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground/70 mb-2">
                  Permissions ({userPerms.permissions.length})
                </div>
                <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
                  {Object.entries(permsByAction).map(([action, perms]) => (
                    <div key={action}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <div className="h-px flex-1 bg-border" />
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-[0.12em]">{action}</span>
                        <div className="h-px flex-1 bg-border" />
                      </div>
                      <div className="space-y-1">
                        {perms.map((p, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 text-xs bg-muted/25 border border-border/50 rounded-md px-2 py-1.5 font-mono"
                          >
                            <span className="text-foreground">{p.resource}</span>
                            {p.scope && (
                              <span className="text-muted-foreground text-xs">within {p.scope}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Shield}
              title="Select a user"
              description="Load a user's roles and permissions from the graph."
            />
          )}
        </div>

        {/* Permission Check Panel */}
        <div
          className="border border-border rounded-xl p-5 space-y-4 relative overflow-hidden"
          style={{ background: "hsl(var(--surface-1, var(--card)))" }}
        >
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-primary/40 to-transparent" />
          <SectionHeader title="Permission Check" />
          <div className="space-y-3">
            <UserSelector value={userId} onChange={setUserId} label="User" />
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Action</label>
                <Select value={checkAction} onValueChange={setCheckAction}>
                  <SelectTrigger className={selectClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ACTIONS.map((a) => (
                      <SelectItem key={a} value={a} className="text-xs font-mono">{a}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Resource</label>
                <Select value={checkResource} onValueChange={setCheckResource}>
                  <SelectTrigger className={selectClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {RESOURCES.map((r) => (
                      <SelectItem key={r} value={r} className="text-xs font-mono">{r}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button onClick={runCheck} disabled={checkLoading} size="sm" className="w-full shadow-glow-sm">
              {checkLoading ? "Checking…" : "Check Permission"}
            </Button>
          </div>

          {checkResult && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "rounded-xl p-4 border space-y-3",
                checkResult.allowed
                  ? "bg-emerald-500/10 border-emerald-500/25"
                  : "bg-red-500/10 border-red-500/25"
              )}
            >
              <PermissionBadge allowed={checkResult.allowed} />
              {checkResult.reason && <p className="text-xs text-muted-foreground">{checkResult.reason}</p>}
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1.5">
                  Policy Path
                </div>
                <PolicyPathViewer path={checkResult.policy_path} compact />
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Policy Sandbox */}
      <PolicySandbox userId={userId} action={checkAction} resource={checkResource} />
    </div>
  );
}

function PolicySandbox({ userId, action, resource }: { userId: string; action: string; resource: string }) {
  const [grantRole, setGrantRole] = useState("");
  const [delegateFrom, setDelegateFrom] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    original: PermissionCheckResponse;
    simulated: PermissionCheckResponse;
    policy_path_diff: string[];
  } | null>(null);

  async function runSimulation() {
    setLoading(true);
    try {
      const res = await api.simulatePolicy({
        user_id: userId,
        action,
        resource_id: resource,
        hypothetical_grants: grantRole ? [{ user_id: userId, role: grantRole }] : [],
        hypothetical_delegations: delegateFrom ? [{ from_user_id: delegateFrom, to_user_id: userId }] : [],
      });
      setResult(res);
    } finally {
      setLoading(false);
    }
  }

  const inputClass = "w-full h-8 rounded-lg border border-border px-3 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40 transition-colors";

  return (
    <div
      className="border border-border rounded-xl p-5 space-y-4 relative overflow-hidden"
      style={{ background: "hsl(var(--surface-1, var(--card)))" }}
    >
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-violet-500/40 to-transparent" />
      <div className="flex items-center gap-2 flex-wrap">
        <Shield className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-semibold text-foreground">Policy Sandbox — What If?</h2>
        <span className="text-xs text-muted-foreground bg-muted/60 px-2 py-0.5 rounded-full border border-border">
          simulation mode — never saved
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">
            Hypothetical grant role to <span className="text-foreground">{userId || "user"}</span>
          </label>
          <input
            className={inputClass}
            style={{ background: "hsl(var(--input))" }}
            placeholder="e.g. pm, admin, approver"
            value={grantRole}
            onChange={(e) => setGrantRole(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">Hypothetical delegation from user</label>
          <input
            className={inputClass}
            style={{ background: "hsl(var(--input))" }}
            placeholder="e.g. jordan"
            value={delegateFrom}
            onChange={(e) => setDelegateFrom(e.target.value)}
          />
        </div>
      </div>

      <Button onClick={runSimulation} disabled={loading || (!grantRole && !delegateFrom)} size="sm" variant="secondary">
        {loading ? "Simulating…" : "Run Simulation"}
      </Button>

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 sm:grid-cols-2 gap-3"
        >
          <div className={cn("rounded-lg p-3 border space-y-2",
            result.original.allowed ? "border-emerald-500/25 bg-emerald-500/5" : "border-red-500/25 bg-red-500/5"
          )}>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-[0.12em]">Current</div>
            <PermissionBadge allowed={result.original.allowed} />
            <PolicyPathViewer path={result.original.policy_path} compact />
          </div>
          <div className={cn("rounded-lg p-3 border space-y-2",
            result.simulated.allowed ? "border-emerald-500/25 bg-emerald-500/8" : "border-red-500/25 bg-red-500/5"
          )}>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-[0.12em]">Simulated</div>
            <PermissionBadge allowed={result.simulated.allowed} />
            <PolicyPathViewer path={result.simulated.policy_path} compact />
          </div>
          {result.policy_path_diff.length > 0 && (
            <div className="sm:col-span-2 space-y-1">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-[0.12em]">Diff</div>
              <div className="space-y-0.5">
                {result.policy_path_diff.map((d, i) => (
                  <div key={i} className={cn("text-xs font-mono px-2.5 py-1 rounded-md",
                    d.startsWith("+") ? "text-emerald-400 bg-emerald-500/10" : "text-red-400 bg-red-500/10"
                  )}>
                    {d}
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}

function PolicyTraceContent({ result }: { result: PermissionCheckResponse }) {
  return (
    <div className="space-y-4">
      <PermissionBadge allowed={result.allowed} />
      {result.reason && <p className="text-xs text-muted-foreground">{result.reason}</p>}
      {result.approver && (
        <div className="text-xs">
          <span className="text-muted-foreground">Approver: </span>
          <span className="text-foreground font-mono">{result.approver}</span>
        </div>
      )}
      <div>
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">
          Full Policy Trace
        </div>
        <PolicyPathViewer path={result.policy_path} />
      </div>
    </div>
  );
}
