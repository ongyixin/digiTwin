import { LoadingState } from "@/components/shared/LoadingState";

export default function DecisionsLoading() {
  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div className="space-y-2">
        <div className="h-8 w-32 bg-muted rounded animate-pulse" />
        <div className="h-4 w-64 bg-muted/60 rounded animate-pulse" />
      </div>
      <LoadingState rows={6} />
    </div>
  );
}
