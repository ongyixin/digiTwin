"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useInspector } from "@/components/providers";
import { ScrollArea } from "@/components/ui/scroll-area";

import type { Transition } from "framer-motion";
const spring: Transition = { type: "spring", stiffness: 320, damping: 32, mass: 0.8 };

export function InspectorPanel() {
  const { inspector, closeInspector } = useInspector();

  return (
    <AnimatePresence>
      {inspector && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 360, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={spring}
          className="shrink-0 border-l border-border h-screen sticky top-0 overflow-hidden"
          style={{ background: "hsl(var(--surface-0, var(--card)))" }}
        >
          {/* Top accent line */}
          <div className="h-px w-full bg-gradient-to-r from-primary/60 to-transparent" />

          <div className="flex flex-col h-full w-[360px]">
            {/* Frosted header */}
            <div
              className="flex items-center justify-between px-5 py-3.5 border-b border-border shrink-0 backdrop-blur-sm"
              style={{ background: "hsl(var(--surface-1, var(--card)) / 0.8)" }}
            >
              <span className="text-sm font-semibold text-foreground truncate">{inspector.title}</span>
              <button
                onClick={closeInspector}
                className="text-muted-foreground hover:text-foreground transition-colors ml-2 shrink-0 hover:bg-surface-2 p-1 rounded"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <ScrollArea className="flex-1">
              <div className="p-5">{inspector.content}</div>
            </ScrollArea>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
