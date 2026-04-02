"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ChevronLeft, ChevronRight, Activity, Cpu } from "lucide-react";
import { motion } from "framer-motion";
import { NAV_ITEMS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useJobs } from "@/lib/hooks";

function SystemStatus({ collapsed }: { collapsed: boolean }) {
  const { data: jobs } = useJobs();
  const hasRunning = jobs?.some((j) => j.status === "running");

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-0/60",
        collapsed && "justify-center px-2"
      )}
    >
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full shrink-0",
          hasRunning
            ? "bg-blue-400 animate-pulse-dot"
            : "bg-emerald-400"
        )}
      />
      {!collapsed && (
        <span className="text-xs text-muted-foreground font-medium">
          {hasRunning ? "Processing…" : "Twin active"}
        </span>
      )}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex flex-col h-screen border-r border-border sticky top-0 shrink-0 transition-all duration-300",
          "bg-[hsl(var(--surface-0,var(--background)))]",
          collapsed ? "w-16" : "w-60"
        )}
      >
        {/* Logo */}
        <div
          className={cn(
            "flex items-center h-14 px-4 border-b border-border gap-2.5 shrink-0",
            collapsed && "justify-center px-2"
          )}
        >
          <div className="w-7 h-7 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center shrink-0 shadow-glow-sm">
            <Cpu className="w-3.5 h-3.5 text-primary" />
          </div>
          {!collapsed && (
            <span className="font-semibold text-foreground tracking-tight text-sm">digiTwin</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4 space-y-5">
          {NAV_ITEMS.map((section) => (
            <div key={section.section}>
              {!collapsed && (
                <div className="px-4 mb-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground/60">
                  {section.section}
                </div>
              )}
              <div className="space-y-0.5 px-2">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const isActive =
                    pathname === item.href ||
                    (item.href !== "/" && pathname.startsWith(item.href));

                  if (collapsed) {
                    return (
                      <Tooltip key={item.href}>
                        <TooltipTrigger asChild>
                          <Link
                            href={item.href}
                            className={cn(
                              "flex items-center justify-center w-10 h-10 mx-auto rounded-lg transition-all duration-150",
                              isActive
                                ? "bg-primary/15 text-primary shadow-glow-sm"
                                : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                            )}
                          >
                            <Icon className="w-4 h-4" />
                          </Link>
                        </TooltipTrigger>
                        <TooltipContent side="right" className="text-xs">
                          <p className="font-medium">{item.label}</p>
                          {item.tooltip && <p className="text-muted-foreground mt-0.5 max-w-[200px]">{item.tooltip}</p>}
                        </TooltipContent>
                      </Tooltip>
                    );
                  }

                  return (
                    <Tooltip key={item.href}>
                      <TooltipTrigger asChild>
                        <motion.div whileHover={{ x: 1 }} transition={{ duration: 0.1 }}>
                          <Link
                            href={item.href}
                            className={cn(
                              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-150 relative",
                              isActive
                                ? "bg-primary/12 text-primary font-medium"
                                : "text-muted-foreground hover:text-foreground hover:bg-surface-2"
                            )}
                          >
                            {isActive && (
                              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-r-full" />
                            )}
                            <Icon className="w-4 h-4 shrink-0" />
                            {item.label}
                          </Link>
                        </motion.div>
                      </TooltipTrigger>
                      {item.tooltip && (
                        <TooltipContent side="right" className="text-xs max-w-[220px]">
                          {item.tooltip}
                        </TooltipContent>
                      )}
                    </Tooltip>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* System status + collapse */}
        <div className="p-2 border-t border-border space-y-1 shrink-0">
          <SystemStatus collapsed={collapsed} />
          <button
            onClick={() => setCollapsed((c) => !c)}
            className={cn(
              "flex items-center justify-center w-full h-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors",
              collapsed && "w-10 mx-auto"
            )}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </aside>
    </TooltipProvider>
  );
}
