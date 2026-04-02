import { useEffect, useRef, useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { JobState, StageInfo, ResolutionStreamEvent } from "./types";

const WS_BASE =
  (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000").replace(/^http/, "ws");

export function useDecisions() {
  return useQuery({
    queryKey: ["decisions"],
    queryFn: () => api.getDecisions(),
  });
}

export function useDecisionLineage(id: string) {
  return useQuery({
    queryKey: ["decision-lineage", id],
    queryFn: () => api.getDecisionLineage(id),
    enabled: !!id,
  });
}

export function useActionHistory() {
  return useQuery({
    queryKey: ["action-history"],
    queryFn: () => api.getActionHistory(),
  });
}

export function useUserPermissions(userId: string) {
  return useQuery({
    queryKey: ["user-permissions", userId],
    queryFn: () => api.getUserPermissions(userId),
    enabled: !!userId,
  });
}

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.listJobs(),
    refetchInterval: 5000,
  });
}

export function useDecisionImpact(id: string) {
  return useQuery({
    queryKey: ["decision-impact", id],
    queryFn: () => api.getDecisionImpact(id),
    enabled: !!id,
  });
}

export function useReviewInbox() {
  return useQuery({
    queryKey: ["review-inbox"],
    queryFn: () => api.getReviewInbox(),
    refetchInterval: 10000,
  });
}

export function useTimeline() {
  return useQuery({
    queryKey: ["timeline"],
    queryFn: () => api.getTimeline(),
  });
}

// ---------------------------------------------------------------------------
// Resolution Engine hooks
// ---------------------------------------------------------------------------

export function useResolutionCases(params?: { status?: string; severity?: string }) {
  return useQuery({
    queryKey: ["resolution-cases", params],
    queryFn: () => api.getResolutionCases(params),
    refetchInterval: 10000,
  });
}

export function useResolutionCase(caseId: string | null) {
  return useQuery({
    queryKey: ["resolution-case", caseId],
    queryFn: () => api.getResolutionCase(caseId!),
    enabled: !!caseId,
    refetchInterval: 5000,
  });
}

export interface ResolutionStreamState {
  events: ResolutionStreamEvent[];
  connected: boolean;
  error: string | null;
}

export function useResolutionStream(caseId: string | null): ResolutionStreamState {
  const [state, setState] = useState<ResolutionStreamState>({
    events: [],
    connected: false,
    error: null,
  });
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!caseId) return;

    const ws = new WebSocket(`${WS_BASE}/api/resolution/ws/${caseId}`);
    wsRef.current = ws;

    ws.onopen = () => setState((s) => ({ ...s, connected: true, error: null }));

    ws.onmessage = (evt) => {
      try {
        const msg: ResolutionStreamEvent = JSON.parse(evt.data);
        if (msg.type === "ping") return;
        setState((s) => ({ ...s, events: [...s.events, msg] }));
      } catch (_) {
        // ignore malformed messages
      }
    };

    ws.onerror = () => setState((s) => ({ ...s, error: "WebSocket error", connected: false }));
    ws.onclose = () => setState((s) => ({ ...s, connected: false }));

    return () => {
      ws.close();
    };
  }, [caseId]);

  return state;
}

// ---------------------------------------------------------------------------
// Speech recognition hook (browser Web Speech API)
// ---------------------------------------------------------------------------

export interface SpeechRecognitionState {
  isListening: boolean;
  isSupported: boolean;
  startListening: () => void;
  stopListening: () => void;
}

export function useSpeechRecognition(
  onResult: (transcript: string) => void
): SpeechRecognitionState {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const SpeechRecognitionAPI =
    typeof window !== "undefined"
      ? (window.SpeechRecognition || (window as Window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition)
      : undefined;

  const isSupported = !!SpeechRecognitionAPI;

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const startListening = useCallback(() => {
    if (!SpeechRecognitionAPI) return;

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => setIsListening(true);

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = "";
      let interimTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }
      onResult(finalTranscript || interimTranscript);
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
  }, [SpeechRecognitionAPI, onResult]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  return { isListening, isSupported, startListening, stopListening };
}

// ---------------------------------------------------------------------------
// WebSocket job stream hook
// ---------------------------------------------------------------------------

export interface JobStreamState {
  job: JobState | null;
  connected: boolean;
  error: string | null;
}

export function useJobStream(jobId: string | null): JobStreamState {
  const [state, setState] = useState<JobStreamState>({
    job: null,
    connected: false,
    error: null,
  });
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) return;

    // First load current job state via REST for immediate render
    api.getJob(jobId).then((job) => {
      setState((s) => ({ ...s, job }));
    }).catch(() => {});

    const ws = new WebSocket(`${WS_BASE}/ws/jobs/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => setState((s) => ({ ...s, connected: true, error: null }));

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "ping") return;

        if (msg.type === "job_snapshot") {
          setState((s) => ({ ...s, job: msg.job }));
          return;
        }

        setState((s) => {
          if (!s.job) return s;
          const job = { ...s.job };

          if (msg.type === "job_started") {
            job.status = "running";
          } else if (msg.type === "stage_started") {
            job.stages = job.stages.map((stage: StageInfo) =>
              stage.name === msg.stage
                ? { ...stage, status: "running", detail: msg.detail, started_at: msg.ts }
                : stage
            );
          } else if (msg.type === "stage_completed") {
            job.stages = job.stages.map((stage: StageInfo) =>
              stage.name === msg.stage
                ? {
                    ...stage,
                    status: "completed",
                    entities_found: msg.entities_found,
                    duration_ms: msg.duration_ms,
                    completed_at: msg.ts,
                  }
                : stage
            );
          } else if (msg.type === "job_completed") {
            job.status = "completed";
            job.entities_created = msg.entities_created;
            job.twin_diff = msg.twin_diff;
          } else if (msg.type === "job_failed") {
            job.status = "failed";
            job.error = msg.error;
            if (msg.stages) {
              job.stages = msg.stages;
            } else {
              // Fallback: mark any still-running stage as failed
              job.stages = job.stages.map((stage: StageInfo) =>
                stage.status === "running" ? { ...stage, status: "failed" } : stage
              );
            }
          }

          return { ...s, job };
        });
      } catch (_) {
        // ignore malformed messages
      }
    };

    ws.onerror = () => setState((s) => ({ ...s, error: "WebSocket error", connected: false }));
    ws.onclose = () => setState((s) => ({ ...s, connected: false }));

    return () => {
      ws.close();
    };
  }, [jobId]);

  return state;
}
