import { cn } from "@/lib/utils";

interface SplitPaneLayoutProps {
  children: React.ReactNode;
  className?: string;
}

export function SplitPaneLayout({ children, className }: SplitPaneLayoutProps) {
  return (
    <div className={cn("flex gap-6 h-full", className)}>
      {children}
    </div>
  );
}

export function SplitPaneMain({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex-1 min-w-0", className)}>
      {children}
    </div>
  );
}
