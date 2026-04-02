"use client";

import { motion } from "framer-motion";
import { ArtifactModal } from "@/components/shared/ArtifactModal";
import { Button } from "@/components/ui/button";
import { PlusCircle, GitBranch, Shield, Activity } from "lucide-react";

const BENEFITS = [
  {
    icon: GitBranch,
    title: "Extract decisions",
    desc: "Automatically surface key decisions from meetings and docs",
    color: "text-blue-400",
    bg: "bg-blue-500/8",
  },
  {
    icon: Shield,
    title: "Enforce permissions",
    desc: "Policy-aware access control across your knowledge graph",
    color: "text-violet-400",
    bg: "bg-violet-500/8",
  },
  {
    icon: Activity,
    title: "Track actions",
    desc: "Audit every agent action with full policy path replay",
    color: "text-emerald-400",
    bg: "bg-emerald-500/8",
  },
];

/* Animated graph constellation behind the hero */
function GraphConstellation() {
  const nodes = [
    { cx: 200, cy: 80, r: 8, color: "hsl(217 91% 60%)" },
    { cx: 340, cy: 140, r: 12, color: "hsl(217 91% 60%)" },
    { cx: 480, cy: 60, r: 6, color: "hsl(263 70% 50%)" },
    { cx: 140, cy: 180, r: 5, color: "hsl(158 64% 52%)" },
    { cx: 560, cy: 160, r: 7, color: "hsl(38 92% 50%)" },
    { cx: 380, cy: 220, r: 5, color: "hsl(158 64% 52%)" },
    { cx: 260, cy: 240, r: 6, color: "hsl(263 70% 50%)" },
    { cx: 500, cy: 240, r: 5, color: "hsl(217 91% 60%)" },
  ];

  const edges = [
    [0, 1], [1, 2], [1, 3], [2, 4], [1, 5], [3, 6], [5, 7], [4, 7], [0, 3],
  ];

  return (
    <svg
      viewBox="0 0 700 300"
      className="w-full max-w-md h-auto opacity-20"
      fill="none"
    >
      <defs>
        <radialGradient id="empty-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="hsl(217 91% 60%)" stopOpacity="0.3" />
          <stop offset="100%" stopColor="hsl(217 91% 60%)" stopOpacity="0" />
        </radialGradient>
      </defs>

      {edges.map(([a, b], i) => (
        <motion.line
          key={i}
          x1={nodes[a].cx} y1={nodes[a].cy}
          x2={nodes[b].cx} y2={nodes[b].cy}
          stroke="hsl(217 91% 60%)"
          strokeWidth="1"
          strokeOpacity={0.4}
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1, delay: 0.3 + i * 0.08, ease: "easeOut" }}
        />
      ))}

      {nodes.map((n, i) => (
        <motion.g key={i}>
          <circle cx={n.cx} cy={n.cy} r={n.r * 2.5} fill="url(#empty-glow)" />
          <motion.circle
            cx={n.cx} cy={n.cy} r={n.r}
            fill={n.color}
            fillOpacity={0.3}
            stroke={n.color}
            strokeWidth="1"
            strokeOpacity={0.5}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 + i * 0.1, ease: "easeOut" }}
          />
        </motion.g>
      ))}
    </svg>
  );
}

export function HeroEmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center py-24 px-8 text-center space-y-10 relative"
    >
      <div className="space-y-6 flex flex-col items-center">
        <GraphConstellation />
        <div className="space-y-3">
          <h2 className="text-3xl font-bold text-foreground">Your digital twin is ready</h2>
          <p className="text-base text-muted-foreground max-w-md mx-auto leading-relaxed">
            Ingest a meeting transcript to begin building your knowledge graph and unlock decision intelligence.
          </p>
        </div>
        <ArtifactModal
          trigger={
            <Button size="lg" className="gap-2 shadow-glow px-8">
              <PlusCircle className="w-5 h-5" />
              Add First Artifact
            </Button>
          }
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 w-full max-w-2xl">
        {BENEFITS.map((b) => {
          const Icon = b.icon;
          return (
            <motion.div
              key={b.title}
              className={`rounded-xl border border-border p-5 text-center ${b.bg}`}
              whileHover={{ y: -2 }}
              transition={{ duration: 0.15 }}
            >
              <div className="flex justify-center mb-3">
                <div className={`p-2.5 rounded-lg ${b.bg}`}>
                  <Icon className={`w-5 h-5 ${b.color}`} />
                </div>
              </div>
              <div className="text-base font-semibold text-foreground mb-1.5">{b.title}</div>
              <div className="text-sm text-muted-foreground leading-relaxed">{b.desc}</div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
