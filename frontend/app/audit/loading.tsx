import { LoadingState } from "@/components/shared/LoadingState";

export default function AuditLoading() {
  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div className="space-y-2">
        <div className="h-8 w-28 bg-muted rounded animate-pulse" />
        <div className="h-4 w-56 bg-muted/60 rounded animate-pulse" />
      </div>
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card border border-border rounded-xl p-3 h-16 animate-pulse" />
        ))}
      </div>
      <LoadingState rows={5} />
    </div>
  );
}
