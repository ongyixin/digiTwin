"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { USERS } from "@/lib/constants";
import { OwnerChip } from "./OwnerChip";

interface UserSelectorProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  users?: string[];
}

export function UserSelector({ value, onChange, label = "Acting as", users = USERS }: UserSelectorProps) {
  return (
    <div className="space-y-1">
      {label && <label className="text-xs font-medium text-muted-foreground">{label}</label>}
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-44 h-8 text-xs bg-[hsl(var(--input))] border-border">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {users.map((u) => (
            <SelectItem key={u} value={u} className="text-xs">
              <OwnerChip name={u} size="sm" />
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
