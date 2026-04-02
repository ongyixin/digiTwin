import {
  LayoutDashboard,
  GitBranch,
  MessageSquare,
  Zap,
  Shield,
  Network,
  ScrollText,
  Database,
  Crosshair,
  BookOpen,
  ClipboardCheck,
} from "lucide-react";

export const NAV_ITEMS = [
  {
    section: "Intelligence",
    items: [
      { label: "Overview", href: "/", icon: LayoutDashboard, tooltip: "High-level summary of system health, recent activity, and key metrics" },
      { label: "Artifacts", href: "/artifacts", icon: Database, tooltip: "Browse and manage tracked documents, outputs, and data produced by the system" },
      { label: "Decisions", href: "/decisions", icon: GitBranch, tooltip: "View and trace all recorded decisions, their rationale, and current status" },
      { label: "Ask the Twin", href: "/ask", icon: MessageSquare, tooltip: "Converse with your digital twin to query knowledge and get AI-powered answers" },
    ],
  },
  {
    section: "Operations",
    items: [
      { label: "Actions", href: "/actions", icon: Zap, tooltip: "Monitor and trigger automated actions and tasks across the system" },
      { label: "Resolution", href: "/resolution", icon: Crosshair, tooltip: "Autonomous engine that identifies and resolves blockers and open issues" },
      { label: "Review", href: "/review", icon: ClipboardCheck, tooltip: "Items awaiting human review and approval before proceeding" },
      { label: "Permissions", href: "/permissions", icon: Shield, tooltip: "Manage access controls and permission policies for users and resources" },
    ],
  },
  {
    section: "System",
    items: [
      { label: "Dependency Map", href: "/dependency-map", icon: Network, tooltip: "Visual graph of relationships and dependencies across system components" },
      { label: "Audit", href: "/audit", icon: ScrollText, tooltip: "Full activity log of all changes and events for compliance and traceability" },
    ],
  },
];

export const SEVERITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  low:      { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30" },
  medium:   { bg: "bg-amber-500/15",   text: "text-amber-400",   border: "border-amber-500/30" },
  high:     { bg: "bg-orange-500/15",  text: "text-orange-400",  border: "border-orange-500/30" },
  critical: { bg: "bg-red-500/15",     text: "text-red-400",     border: "border-red-500/30" },
};

export const GRAPH_NODE_COLORS: Record<string, string> = {
  Decision: "#3b82f6",
  Assumption: "#f59e0b",
  Evidence: "#10b981",
  Task: "#8b5cf6",
  Approval: "#ef4444",
  Person: "#64748b",
  Meeting: "#0ea5e9",
  Node: "#94a3b8",
  ResolutionCase: "#f97316",
  ProposedAction: "#06b6d4",
};

export const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  proposed: { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30" },
  approved: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30" },
  superseded: { bg: "bg-zinc-500/15", text: "text-zinc-400", border: "border-zinc-500/30" },
  rejected: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30" },
  active: { bg: "bg-blue-500/15", text: "text-blue-400", border: "border-blue-500/30" },
  validated: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30" },
  contradicted: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30" },
  pending: { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30" },
  allowed: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30" },
  blocked: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30" },
  denied: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30" },
  escalated: { bg: "bg-violet-500/15", text: "text-violet-400", border: "border-violet-500/30" },
  // Resolution Engine statuses
  planning: { bg: "bg-blue-500/15", text: "text-blue-400", border: "border-blue-500/30" },
  executing: { bg: "bg-blue-500/15", text: "text-blue-400", border: "border-blue-500/30" },
  awaiting_review: { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30" },
  monitoring: { bg: "bg-violet-500/15", text: "text-violet-400", border: "border-violet-500/30" },
  resolved: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30" },
  failed: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30" },
  cancelled: { bg: "bg-zinc-500/15", text: "text-zinc-400", border: "border-zinc-500/30" },
  executed: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30" },
  queued_for_review: { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30" },
};

export const USERS = ["alex", "jordan", "sam", "riley"];
export const ACTIONS = ["view", "edit", "execute", "approve", "delegate"];
export const RESOURCES = ["send-reminder", "escalate", "edit-decisions", "approve-launch", "view-all"];
