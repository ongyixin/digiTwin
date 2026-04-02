import { LoadingState } from "@/components/shared/LoadingState";

export default function ResolutionCaseLoading() {
  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <LoadingState rows={6} />
    </div>
  );
}
