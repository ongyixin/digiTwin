"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

/* ── Node / edge types ─────────────────────────────────────── */
interface GNode {
  cx: number;
  cy: number;
  r: number;
  delay: number;
  color: string;
}

type Edge = [number, number];

interface GraphPattern {
  nodes: GNode[];
  edges: Edge[];
}

/* ── Color palette ─────────────────────────────────────────── */
const BLUE    = "#3b82f6";
const VIOLET  = "#8b5cf6";
const EMERALD = "#10b981";
const AMBER   = "#f59e0b";
const RED     = "#ef4444";
const CYAN    = "#0ea5e9";

/* ── Pattern 1 — Wide mesh network ─────────────────────────── */
const PATTERN_1: GraphPattern = {
  nodes: [
    { cx: 80,   cy: 55,  r: 6,  delay: 0,    color: BLUE },
    { cx: 210,  cy: 35,  r: 5,  delay: 0.15, color: VIOLET },
    { cx: 350,  cy: 75,  r: 8,  delay: 0.3,  color: BLUE },
    { cx: 490,  cy: 25,  r: 5,  delay: 0.08, color: EMERALD },
    { cx: 610,  cy: 65,  r: 7,  delay: 0.22, color: AMBER },
    { cx: 730,  cy: 45,  r: 5,  delay: 0.4,  color: VIOLET },
    { cx: 870,  cy: 85,  r: 6,  delay: 0.12, color: BLUE },
    { cx: 145,  cy: 130, r: 5,  delay: 0.2,  color: EMERALD },
    { cx: 310,  cy: 155, r: 7,  delay: 0.28, color: AMBER },
    { cx: 530,  cy: 140, r: 5,  delay: 0.36, color: BLUE },
    { cx: 690,  cy: 120, r: 8,  delay: 0.44, color: RED },
    { cx: 810,  cy: 165, r: 5,  delay: 0.5,  color: VIOLET },
    { cx: 960,  cy: 55,  r: 6,  delay: 0.08, color: EMERALD },
    { cx: 1060, cy: 110, r: 5,  delay: 0.25, color: BLUE },
    { cx: 430,  cy: 175, r: 5,  delay: 0.16, color: RED },
    { cx: 160,  cy: 200, r: 4,  delay: 0.35, color: AMBER },
    { cx: 560,  cy: 210, r: 4,  delay: 0.42, color: VIOLET },
    { cx: 780,  cy: 225, r: 4,  delay: 0.48, color: EMERALD },
    { cx: 1000, cy: 180, r: 5,  delay: 0.3,  color: BLUE },
  ],
  edges: [
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6],
    [7, 8], [8, 9], [9, 10], [10, 11],
    [0, 7], [1, 8], [2, 9], [4, 10], [6, 11],
    [3, 14], [5, 13], [12, 6], [12, 13],
    [7, 15], [14, 16], [11, 17], [13, 18],
    [8, 14], [9, 16], [10, 17], [2, 8],
  ],
};

/* ── Pattern 2 — Star / hub-and-spoke ──────────────────────── */
const PATTERN_2: GraphPattern = {
  nodes: [
    // Central hub
    { cx: 550, cy: 120, r: 10, delay: 0,    color: BLUE },
    // Inner ring
    { cx: 380, cy: 60,  r: 6,  delay: 0.1,  color: VIOLET },
    { cx: 720, cy: 60,  r: 6,  delay: 0.12, color: EMERALD },
    { cx: 380, cy: 180, r: 6,  delay: 0.14, color: AMBER },
    { cx: 720, cy: 180, r: 6,  delay: 0.16, color: RED },
    { cx: 250, cy: 120, r: 6,  delay: 0.18, color: CYAN },
    { cx: 850, cy: 120, r: 6,  delay: 0.2,  color: VIOLET },
    // Outer ring
    { cx: 120, cy: 50,  r: 4,  delay: 0.25, color: BLUE },
    { cx: 200, cy: 200, r: 4,  delay: 0.28, color: EMERALD },
    { cx: 550, cy: 20,  r: 5,  delay: 0.3,  color: AMBER },
    { cx: 900, cy: 40,  r: 4,  delay: 0.32, color: RED },
    { cx: 980, cy: 170, r: 4,  delay: 0.34, color: BLUE },
    { cx: 550, cy: 230, r: 5,  delay: 0.36, color: VIOLET },
    { cx: 100, cy: 150, r: 4,  delay: 0.38, color: AMBER },
    { cx: 1000, cy: 90, r: 4,  delay: 0.4,  color: CYAN },
    // Satellite clusters
    { cx: 60,  cy: 90,  r: 3,  delay: 0.42, color: EMERALD },
    { cx: 1040, cy: 140, r: 3, delay: 0.44, color: BLUE },
  ],
  edges: [
    // Hub to inner
    [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6],
    // Inner to outer
    [1, 7], [1, 9], [5, 7], [5, 8], [2, 9], [2, 10],
    [6, 10], [6, 11], [4, 11], [4, 12], [3, 12], [3, 8],
    // Outer connections
    [7, 15], [13, 15], [5, 13], [11, 16], [6, 14], [14, 16],
    // Inner ring cross-connections
    [1, 5], [2, 6], [3, 5], [4, 6],
  ],
};

/* ── Pattern 3 — Layered clusters ──────────────────────────── */
const PATTERN_3: GraphPattern = {
  nodes: [
    // Left cluster
    { cx: 120, cy: 80,  r: 7,  delay: 0,    color: BLUE },
    { cx: 60,  cy: 40,  r: 4,  delay: 0.08, color: VIOLET },
    { cx: 60,  cy: 130, r: 4,  delay: 0.1,  color: BLUE },
    { cx: 180, cy: 40,  r: 5,  delay: 0.12, color: EMERALD },
    { cx: 180, cy: 130, r: 4,  delay: 0.14, color: AMBER },
    { cx: 120, cy: 170, r: 3,  delay: 0.16, color: CYAN },
    // Center cluster
    { cx: 440, cy: 100, r: 9,  delay: 0.05, color: EMERALD },
    { cx: 370, cy: 50,  r: 5,  delay: 0.15, color: BLUE },
    { cx: 510, cy: 50,  r: 5,  delay: 0.18, color: VIOLET },
    { cx: 370, cy: 160, r: 5,  delay: 0.2,  color: RED },
    { cx: 510, cy: 160, r: 6,  delay: 0.22, color: AMBER },
    { cx: 440, cy: 200, r: 4,  delay: 0.24, color: CYAN },
    // Right cluster
    { cx: 780, cy: 90,  r: 7,  delay: 0.1,  color: RED },
    { cx: 720, cy: 40,  r: 5,  delay: 0.2,  color: BLUE },
    { cx: 850, cy: 50,  r: 4,  delay: 0.22, color: AMBER },
    { cx: 720, cy: 150, r: 4,  delay: 0.25, color: VIOLET },
    { cx: 850, cy: 140, r: 5,  delay: 0.28, color: EMERALD },
    // Far-right satellite
    { cx: 980, cy: 80,  r: 5,  delay: 0.3,  color: CYAN },
    { cx: 1040, cy: 130, r: 3, delay: 0.35, color: BLUE },
    // Bridge nodes
    { cx: 280, cy: 90,  r: 4,  delay: 0.18, color: AMBER },
    { cx: 630, cy: 90,  r: 4,  delay: 0.26, color: VIOLET },
  ],
  edges: [
    // Left cluster
    [0, 1], [0, 2], [0, 3], [0, 4], [2, 5], [4, 5], [1, 3],
    // Center cluster
    [6, 7], [6, 8], [6, 9], [6, 10], [9, 11], [10, 11], [7, 8],
    // Right cluster
    [12, 13], [12, 14], [12, 15], [12, 16], [13, 14], [15, 16],
    // Far right
    [14, 17], [16, 17], [17, 18],
    // Bridges between clusters
    [0, 19], [19, 6], [3, 19], [6, 20], [20, 12], [8, 20],
    [4, 9], [10, 15],
  ],
};

/* ── Pattern 4 — DNA / double helix inspired ───────────────── */
const PATTERN_4: GraphPattern = {
  nodes: [
    // Top strand
    { cx: 100, cy: 40,  r: 5,  delay: 0,    color: BLUE },
    { cx: 250, cy: 60,  r: 6,  delay: 0.06, color: VIOLET },
    { cx: 400, cy: 35,  r: 5,  delay: 0.12, color: BLUE },
    { cx: 550, cy: 55,  r: 7,  delay: 0.18, color: EMERALD },
    { cx: 700, cy: 40,  r: 5,  delay: 0.24, color: BLUE },
    { cx: 850, cy: 65,  r: 6,  delay: 0.3,  color: VIOLET },
    { cx: 1000, cy: 45, r: 5,  delay: 0.36, color: EMERALD },
    // Bottom strand
    { cx: 100, cy: 200, r: 5,  delay: 0.03, color: AMBER },
    { cx: 250, cy: 180, r: 6,  delay: 0.09, color: RED },
    { cx: 400, cy: 205, r: 5,  delay: 0.15, color: AMBER },
    { cx: 550, cy: 185, r: 7,  delay: 0.21, color: RED },
    { cx: 700, cy: 200, r: 5,  delay: 0.27, color: AMBER },
    { cx: 850, cy: 175, r: 6,  delay: 0.33, color: RED },
    { cx: 1000, cy: 195, r: 5, delay: 0.39, color: AMBER },
    // Cross rungs
    { cx: 175, cy: 120, r: 4,  delay: 0.1,  color: CYAN },
    { cx: 325, cy: 120, r: 4,  delay: 0.16, color: CYAN },
    { cx: 475, cy: 120, r: 5,  delay: 0.22, color: CYAN },
    { cx: 625, cy: 120, r: 4,  delay: 0.28, color: CYAN },
    { cx: 775, cy: 120, r: 4,  delay: 0.34, color: CYAN },
    { cx: 925, cy: 120, r: 5,  delay: 0.4,  color: CYAN },
  ],
  edges: [
    // Top strand
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6],
    // Bottom strand
    [7, 8], [8, 9], [9, 10], [10, 11], [11, 12], [12, 13],
    // Cross rungs connecting strands
    [0, 14], [14, 8], [1, 14],
    [1, 15], [15, 9], [2, 15],
    [2, 16], [16, 10], [3, 16],
    [3, 17], [17, 11], [4, 17],
    [4, 18], [18, 12], [5, 18],
    [5, 19], [19, 13], [6, 19],
    // Top to bottom diagonal connections
    [0, 7], [6, 13],
  ],
};

const PATTERNS = [PATTERN_1, PATTERN_2, PATTERN_3, PATTERN_4];
const CYCLE_INTERVAL = 8000; // ms between transitions

/* ── Glow ID lookup ────────────────────────────────────────── */
function glowId(color: string): string {
  switch (color) {
    case BLUE:    return "node-glow-blue";
    case VIOLET:  return "node-glow-violet";
    case EMERALD: return "node-glow-emerald";
    case AMBER:   return "node-glow-amber";
    case RED:     return "node-glow-red";
    case CYAN:    return "node-glow-cyan";
    default:      return "node-glow-blue";
  }
}

/* ── Single rendered graph ─────────────────────────────────── */
function GraphSVG({ pattern }: { pattern: GraphPattern }) {
  const { nodes, edges } = pattern;

  return (
    <svg
      className="absolute top-0 left-0 w-full h-[280px]"
      viewBox="0 0 1100 260"
      preserveAspectRatio="xMidYMid slice"
      fill="none"
    >
      {/* Edges */}
      {edges.map(([a, b], i) => {
        const colA = nodes[a].color;
        const colB = nodes[b].color;
        return (
          <motion.line
            key={`e-${i}`}
            x1={nodes[a].cx} y1={nodes[a].cy}
            x2={nodes[b].cx} y2={nodes[b].cy}
            stroke={colA}
            strokeWidth="1.5"
            strokeOpacity={0.45}
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 1.2, delay: 0.05 + i * 0.03, ease: "easeOut" }}
          />
        );
      })}

      {/* Bloom layer */}
      <g filter="url(#bloom-lg)">
        {nodes.map((n, i) => (
          <motion.circle
            key={`bloom-${i}`}
            cx={n.cx} cy={n.cy} r={n.r * 1.5}
            fill={n.color}
            fillOpacity={0.5}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 0.5 }}
            transition={{ duration: 0.6, delay: n.delay + 0.15, ease: "easeOut" }}
          />
        ))}
      </g>

      {/* Nodes with halos */}
      {nodes.map((n, i) => (
        <motion.g key={`n-${i}`}>
          <circle cx={n.cx} cy={n.cy} r={n.r * 4} fill={`url(#${glowId(n.color)})`} />
          <motion.circle
            cx={n.cx} cy={n.cy} r={n.r}
            fill={n.color}
            fillOpacity={0.7}
            stroke={n.color}
            strokeWidth="1.5"
            strokeOpacity={0.9}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: n.delay + 0.15, ease: "easeOut" }}
          />
          <motion.circle
            cx={n.cx} cy={n.cy} r={n.r * 0.35}
            fill="white"
            fillOpacity={0.6}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3, delay: n.delay + 0.45, ease: "easeOut" }}
          />
        </motion.g>
      ))}
    </svg>
  );
}

/* ── Shared SVG defs (gradients + filters) ─────────────────── */
function SharedDefs() {
  return (
    <svg className="absolute w-0 h-0" aria-hidden="true">
      <defs>
        {/* Per-color radial glows */}
        {[
          { id: "node-glow-blue",    color: BLUE },
          { id: "node-glow-violet",  color: VIOLET },
          { id: "node-glow-emerald", color: EMERALD },
          { id: "node-glow-amber",   color: AMBER },
          { id: "node-glow-red",     color: RED },
          { id: "node-glow-cyan",    color: CYAN },
        ].map(({ id, color }) => (
          <radialGradient key={id} id={id} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={color} stopOpacity="0.6" />
            <stop offset="60%" stopColor={color} stopOpacity="0.15" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </radialGradient>
        ))}
        {/* Bloom filters */}
        <filter id="bloom">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" />
        </filter>
        <filter id="bloom-lg">
          <feGaussianBlur in="SourceGraphic" stdDeviation="6" />
        </filter>
      </defs>
    </svg>
  );
}

/* ── Exported cycling background ───────────────────────────── */
interface CyclingGraphBackgroundProps {
  /** Overall opacity of the graph layer (0–1). Defaults to 1 (full). */
  opacity?: number;
}

export function CyclingGraphBackground({ opacity = 1 }: CyclingGraphBackgroundProps) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1) % PATTERNS.length);
    }, CYCLE_INTERVAL);
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      className="absolute inset-0 overflow-hidden pointer-events-none"
      aria-hidden="true"
      style={{ opacity }}
    >
      <SharedDefs />

      <AnimatePresence mode="wait">
        <motion.div
          key={index}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.2, ease: "easeInOut" }}
          className="absolute inset-0"
        >
          <GraphSVG pattern={PATTERNS[index]} />
        </motion.div>
      </AnimatePresence>

      {/* Soft fade-out edges */}
      <div className="absolute bottom-0 left-0 right-0 h-[120px] bg-gradient-to-t from-background to-transparent" />
      <div className="absolute top-0 left-0 w-[200px] h-[280px] bg-gradient-to-r from-background to-transparent" />
      <div className="absolute top-0 right-0 w-[200px] h-[280px] bg-gradient-to-l from-background to-transparent" />
    </div>
  );
}
