import { Loader2 } from "lucide-react";

export default function JobsLoading() {
  return (
    <div className="flex items-center justify-center min-h-[40vh] text-muted-foreground">
      <Loader2 className="w-5 h-5 animate-spin mr-2" />
      <span className="text-sm">Loading job…</span>
    </div>
  );
}
