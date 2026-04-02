import Link from "next/link";
import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  title: string;
  viewAllHref?: string;
  count?: number;
  className?: string;
}

export function SectionHeader({ title, viewAllHref, count, className }: SectionHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between", className)}>
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-foreground">{title}</span>
        {count !== undefined && (
          <span className="text-xs font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">
            {count}
          </span>
        )}
      </div>
      {viewAllHref && (
        <Link
          href={viewAllHref}
          className="text-xs text-muted-foreground hover:text-primary transition-colors"
        >
          View all →
        </Link>
      )}
    </div>
  );
}
