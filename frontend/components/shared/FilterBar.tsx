"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface FilterOption {
  value: string;
  label: string;
}

interface FilterConfig {
  key: string;
  label: string;
  options: FilterOption[];
  value: string;
  onChange: (value: string) => void;
}

interface FilterBarProps {
  search?: {
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
  };
  filters?: FilterConfig[];
  className?: string;
}

export function FilterBar({ search, filters, className }: FilterBarProps) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {search && (
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            value={search.value}
            onChange={(e) => search.onChange(e.target.value)}
            placeholder={search.placeholder ?? "Search…"}
            className={cn(
              "h-8 pl-8 pr-3 text-xs rounded-lg w-56",
              "bg-[hsl(var(--input))] border border-border",
              "text-foreground placeholder:text-muted-foreground/60",
              "focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/40",
              "transition-colors"
            )}
          />
        </div>
      )}
      {filters?.map((f) => (
        <Select key={f.key} value={f.value} onValueChange={f.onChange}>
          <SelectTrigger
            className={cn(
              "h-8 text-xs w-36 bg-[hsl(var(--input))] border-border",
              "focus:ring-primary/50 focus:border-primary/40"
            )}
          >
            <SelectValue placeholder={f.label} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" className="text-xs">
              All {f.label}
            </SelectItem>
            {f.options.map((o) => (
              <SelectItem key={o.value} value={o.value} className="text-xs">
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}
    </div>
  );
}
