"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import type { ArtifactType } from "@/lib/types";
import {
  FileText,
  FileAudio,
  FileVideo,
  Github,
  Shield,
  Layout,
  Loader2,
  PlusCircle,
  ChevronLeft,
  Upload,
  Sparkles,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Client-side transcript metadata extraction
// ---------------------------------------------------------------------------

interface TranscriptMeta {
  title: string | null;
  participants: string[];
}

function extractTranscriptMetadata(text: string): TranscriptMeta {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);

  // Title: look for explicit header markers in the first 10 non-empty lines
  let title: string | null = null;
  const titlePatterns = [
    /^(?:meeting|subject|title|topic|re|regarding):\s*(.+)/i,
    /^#{1,3}\s+(.+)/,
  ];
  for (const line of lines.slice(0, 10)) {
    for (const pat of titlePatterns) {
      const m = line.match(pat);
      if (m?.[1]?.trim()) {
        title = m[1].trim();
        break;
      }
    }
    if (title) break;
  }

  // Participants: collect unique speaker labels (e.g. "Alice:", "John Smith:")
  const speakerRe = /^([A-Z][A-Za-z .'-]{1,40})(?:\s*\[[^\]]*\])?:\s/gm;
  const seen = new Set<string>();
  let m: RegExpExecArray | null;
  while ((m = speakerRe.exec(text)) !== null) {
    seen.add(m[1].trim());
  }

  return { title, participants: Array.from(seen) };
}

interface ArtifactTypeOption {
  type: ArtifactType;
  label: string;
  description: string;
  icon: React.ReactNode;
  accentColor: string;
  accentBg: string;
  accentBar: string;
  acceptedFormats?: string;
  supportsUrl?: boolean;
  supportsGitHub?: boolean;
}

const ARTIFACT_TYPES: ArtifactTypeOption[] = [
  {
    type: "transcript",
    label: "Meeting Transcript",
    description: "Meeting, interview, or support call transcript",
    icon: <FileText className="w-5 h-5" />,
    accentColor: "text-blue-400",
    accentBg: "bg-blue-500/10",
    accentBar: "bg-blue-500",
    acceptedFormats: ".txt,.vtt,.srt,.pdf",
  },
  {
    type: "policy_doc",
    label: "Policy / Compliance",
    description: "Policy, compliance requirement, or regulatory document",
    icon: <Shield className="w-5 h-5" />,
    accentColor: "text-amber-400",
    accentBg: "bg-amber-500/10",
    accentBar: "bg-amber-500",
    acceptedFormats: ".pdf,.docx,.txt",
  },
  {
    type: "prd",
    label: "PRD / RFC / Design Spec",
    description: "Product requirements, RFC, or design specification",
    icon: <Layout className="w-5 h-5" />,
    accentColor: "text-violet-400",
    accentBg: "bg-violet-500/10",
    accentBar: "bg-violet-500",
    acceptedFormats: ".pdf,.docx,.md,.txt",
  },
  {
    type: "audio",
    label: "Audio Recording",
    description: "Audio recording from a meeting or call",
    icon: <FileAudio className="w-5 h-5" />,
    accentColor: "text-emerald-400",
    accentBg: "bg-emerald-500/10",
    accentBar: "bg-emerald-500",
    acceptedFormats: ".mp3,.wav,.m4a,.aac,.ogg",
  },
  {
    type: "video",
    label: "Video Recording",
    description: "Video recording with spoken content",
    icon: <FileVideo className="w-5 h-5" />,
    accentColor: "text-emerald-400",
    accentBg: "bg-emerald-500/10",
    accentBar: "bg-emerald-500",
    acceptedFormats: ".mp4,.webm,.mov,.mkv",
  },
  {
    type: "github_repo",
    label: "GitHub Repository",
    description: "Ingest a GitHub repository's code and docs",
    icon: <Github className="w-5 h-5" />,
    accentColor: "text-zinc-300",
    accentBg: "bg-zinc-500/10",
    accentBar: "bg-zinc-400",
    supportsUrl: false,
    supportsGitHub: true,
  },
  {
    type: "generic_text",
    label: "Generic Text",
    description: "Any text document or data dump",
    icon: <FileText className="w-5 h-5" />,
    accentColor: "text-muted-foreground",
    accentBg: "bg-muted/60",
    accentBar: "bg-muted-foreground",
    acceptedFormats: ".txt,.md,.rst",
    supportsUrl: true,
  },
];

interface ArtifactModalProps {
  trigger?: React.ReactNode;
}

export function ArtifactModal({ trigger }: ArtifactModalProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"choose" | "configure">("choose");
  const [selectedType, setSelectedType] = useState<ArtifactTypeOption | null>(null);

  const [title, setTitle] = useState("");
  const [sensitivity, setSensitivity] = useState("internal");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [transcriptText, setTranscriptText] = useState("");
  const [meetingDate, setMeetingDate] = useState("2026-04-01");
  const [participants, setParticipants] = useState("");
  const [repoUrl, setRepoUrl] = useState("");

  // Auto-detection state
  const [autoTitle, setAutoTitle] = useState(false);
  const [autoParticipants, setAutoParticipants] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track whether the user has manually touched each field
  const titleTouchedRef = useRef(false);
  const participantsTouchedRef = useRef(false);
  const [branch, setBranch] = useState("main");
  const [branches, setBranches] = useState<string[]>([]);
  const [branchesLoading, setBranchesLoading] = useState(false);
  const [branchError, setBranchError] = useState("");

  // Auto-extract title + participants from transcript text (debounced 400 ms)
  useEffect(() => {
    if (selectedType?.type !== "transcript") return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      applyExtraction(transcriptText);
    }, 400);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transcriptText, selectedType]);

  function applyExtraction(text: string) {
    if (!text.trim()) return;
    const meta = extractTranscriptMetadata(text);
    if (meta.title && !titleTouchedRef.current) {
      setTitle(meta.title);
      setAutoTitle(true);
    }
    if (meta.participants.length > 0 && !participantsTouchedRef.current) {
      setParticipants(meta.participants.join(", "));
      setAutoParticipants(true);
    }
  }

  async function handleRepoUrlChange(url: string) {
    setRepoUrl(url);
    setBranches([]);
    setBranchError("");

    const match = url.match(/github\.com\/([^/]+\/[^/\s?#]+)/);
    if (match) {
      setTitle(match[1].replace(/\.git$/, ""));

      setBranchesLoading(true);
      try {
        const data = await api.getGitHubBranches(url.trim());
        setBranches(data.branches);
        setBranch(data.default_branch);
      } catch {
        setBranchError("Could not fetch branches — check URL or token");
        setBranch("main");
      } finally {
        setBranchesLoading(false);
      }
    }
  }

  function reset() {
    setStep("choose");
    setSelectedType(null);
    setTitle("");
    setSensitivity("internal");
    setFile(null);
    setTranscriptText("");
    setMeetingDate("2026-04-01");
    setParticipants("");
    setRepoUrl("");
    setBranch("main");
    setBranches([]);
    setBranchError("");
    setError("");
    setAutoTitle(false);
    setAutoParticipants(false);
    titleTouchedRef.current = false;
    participantsTouchedRef.current = false;
  }

  function handleClose() {
    setOpen(false);
    setTimeout(reset, 300);
  }

  function handleTypeSelect(opt: ArtifactTypeOption) {
    setSelectedType(opt);
    setStep("configure");
  }

  async function handleIngest() {
    if (!selectedType) return;
    setLoading(true);
    setError("");

    try {
      let jobId: string;

      if (selectedType.supportsGitHub) {
        if (!repoUrl) throw new Error("Repository URL is required");
        const res = await api.ingestArtifactUrl({
          artifact_type: selectedType.type,
          source_type: "github",
          github_repo_url: repoUrl,
          github_branch: branch || "main",
          sensitivity,
          metadata: { title: title || repoUrl },
        });
        jobId = res.job_id;
      } else if (selectedType.type === "transcript" && transcriptText) {
        const res = await api.ingestText({
          transcript: transcriptText,
          meeting_title: title || "Untitled Meeting",
          meeting_date: meetingDate,
          participants: participants.split(",").map((p) => p.trim()).filter(Boolean),
        });
        jobId = res.job_id;
      } else {
        const formData = new FormData();
        if (file) formData.append("file", file);
        formData.append("artifact_type", selectedType.type);
        formData.append("sensitivity", sensitivity);
        formData.append("meeting_title", title || file?.name || "");
        formData.append("meeting_date", meetingDate);
        formData.append("participants", participants);
        formData.append("metadata", JSON.stringify({ title: title || file?.name || "" }));
        if (selectedType.type === "transcript" && transcriptText) {
          const blob = new Blob([transcriptText], { type: "text/plain" });
          formData.set("file", blob, "transcript.txt");
        }
        const res = await api.ingestArtifact(formData);
        jobId = res.job_id;
      }

      setOpen(false);
      router.push(`/jobs/${jobId}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ingestion failed");
      setLoading(false);
    }
  }

  const canSubmit = (() => {
    if (!selectedType) return false;
    if (selectedType.supportsGitHub) return !!repoUrl;
    if (selectedType.type === "transcript") return !!(transcriptText || file);
    return !!file;
  })();

  const inputClass =
    "h-8 text-xs bg-[hsl(var(--input))] border-border focus:ring-primary/40 focus:border-primary/40";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button size="sm" className="gap-2 shadow-glow-sm">
            <PlusCircle className="w-4 h-4" />
            Add Artifact
          </Button>
        )}
      </DialogTrigger>

      <DialogContent
        className="max-w-2xl border-border"
        style={{ background: "hsl(var(--surface-1, var(--card)))" }}
      >
        {/* Top accent line */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-primary/60 to-transparent rounded-t-xl" />

        <DialogHeader className="pb-0">
          <DialogTitle className="text-base">
            {step === "choose" ? (
              "Add Artifact"
            ) : (
              <button
                onClick={() => setStep("choose")}
                className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                <span className={selectedType?.accentColor}>{selectedType?.label}</span>
              </button>
            )}
          </DialogTitle>
        </DialogHeader>

        <AnimatePresence mode="wait">
          {step === "choose" && (
            <motion.div
              key="choose"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="grid grid-cols-2 gap-2 mt-2"
            >
              {ARTIFACT_TYPES.map((opt, i) => (
                <motion.button
                  key={opt.type}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.15 }}
                  onClick={() => handleTypeSelect(opt)}
                  className="flex items-start gap-3 p-3.5 rounded-xl border border-border hover:border-primary/40 transition-all text-left group relative overflow-hidden"
                  style={{ background: "hsl(var(--surface-2, var(--muted)))" }}
                >
                  {/* Left accent bar */}
                  <div className={`absolute left-0 top-2 bottom-2 w-0.5 rounded-r-full ${opt.accentBar} opacity-0 group-hover:opacity-100 transition-opacity`} />
                  <span className={`mt-0.5 p-1.5 rounded-lg ${opt.accentBg} ${opt.accentColor} shrink-0`}>
                    {opt.icon}
                  </span>
                  <div>
                    <div className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                      {opt.label}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{opt.description}</div>
                  </div>
                </motion.button>
              ))}
            </motion.div>
          )}

          {step === "configure" && selectedType && (
            <motion.div
              key="configure"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="space-y-4 mt-2"
            >
              {/* Common fields — hidden for GitHub repos (auto-derived) */}
              {!selectedType.supportsGitHub && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                      Title
                      {autoTitle && (
                        <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded-full">
                          <Sparkles className="w-2.5 h-2.5" /> auto
                        </span>
                      )}
                    </label>
                    <Input
                      value={title}
                      onChange={(e) => {
                        setTitle(e.target.value);
                        titleTouchedRef.current = true;
                        setAutoTitle(false);
                      }}
                      placeholder="Document title"
                      className={inputClass}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Sensitivity</label>
                    <Select value={sensitivity} onValueChange={setSensitivity}>
                      <SelectTrigger className={`${inputClass} w-full`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="public" className="text-xs">Public</SelectItem>
                        <SelectItem value="internal" className="text-xs">Internal</SelectItem>
                        <SelectItem value="confidential" className="text-xs">Confidential</SelectItem>
                        <SelectItem value="restricted" className="text-xs">Restricted</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {/* GitHub fields */}
              {selectedType.supportsGitHub && (
                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">
                      <Github className="inline w-3 h-3 mr-1 -mt-0.5" />
                      Repository URL
                    </label>
                    <Input
                      value={repoUrl}
                      onChange={(e) => handleRepoUrlChange(e.target.value)}
                      placeholder="https://github.com/owner/repo"
                      className={inputClass}
                    />
                    {title && (
                      <p className="text-xs text-muted-foreground pl-0.5">
                        Detected: <span className="text-foreground font-mono">{title}</span>
                      </p>
                    )}
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                      Branch
                      {branchesLoading && (
                        <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
                      )}
                    </label>
                    {branches.length > 0 ? (
                      <Select value={branch} onValueChange={setBranch}>
                        <SelectTrigger className={`${inputClass} w-full`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {branches.map((b) => (
                            <SelectItem key={b} value={b} className="text-xs font-mono">
                              {b}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={branch}
                        onChange={(e) => setBranch(e.target.value)}
                        placeholder={branchesLoading ? "Detecting branches…" : "main"}
                        disabled={branchesLoading}
                        className={inputClass}
                      />
                    )}
                    {branchError && (
                      <p className="text-xs text-amber-400 pl-0.5">{branchError}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Transcript fields */}
              {selectedType.type === "transcript" && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-muted-foreground">Date</label>
                      <Input
                        type="date"
                        value={meetingDate}
                        onChange={(e) => setMeetingDate(e.target.value)}
                        className={inputClass}
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                        Participants
                        {autoParticipants && (
                          <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded-full">
                            <Sparkles className="w-2.5 h-2.5" /> auto
                          </span>
                        )}
                      </label>
                      <Input
                        value={participants}
                        onChange={(e) => {
                          setParticipants(e.target.value);
                          participantsTouchedRef.current = true;
                          setAutoParticipants(false);
                        }}
                        placeholder="Alex, Jordan, Sam"
                        className={inputClass}
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">
                      Transcript (paste or upload file below)
                    </label>
                    <textarea
                      className="w-full rounded-lg border border-border px-3 py-2 text-xs h-28 resize-none focus:outline-none focus:ring-1 focus:ring-primary/40 focus:border-primary/40 font-mono text-foreground placeholder:text-muted-foreground/50 transition-colors"
                      style={{ background: "hsl(var(--input))" }}
                      value={transcriptText}
                      onChange={(e) => setTranscriptText(e.target.value)}
                      placeholder="Paste your meeting transcript here…"
                    />
                  </div>
                </div>
              )}

              {/* File upload */}
              {!selectedType.supportsGitHub && (
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">
                    {selectedType.type === "transcript" ? "Or upload file" : "Upload file"}
                    {selectedType.acceptedFormats && (
                      <span className="ml-1 text-muted-foreground/50">({selectedType.acceptedFormats})</span>
                    )}
                  </label>
                  <label className="flex items-center gap-2.5 cursor-pointer border border-dashed border-border rounded-xl px-4 py-3.5 hover:border-primary/50 hover:bg-primary/4 transition-all group">
                    <Upload className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                    <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                      {file ? file.name : "Click to choose a file"}
                    </span>
                    <input
                      type="file"
                      className="hidden"
                      accept={selectedType.acceptedFormats}
                      onChange={(e) => {
                        const picked = e.target.files?.[0] ?? null;
                        setFile(picked);
                        // For text-based transcript files, read content and auto-extract
                        if (
                          picked &&
                          selectedType.type === "transcript" &&
                          /\.(txt|vtt|srt)$/i.test(picked.name)
                        ) {
                          const reader = new FileReader();
                          reader.onload = (ev) => {
                            const text = ev.target?.result as string;
                            if (text) {
                              setTranscriptText("");
                              applyExtraction(text);
                            }
                          };
                          reader.readAsText(picked);
                        }
                        // Pre-fill title from filename if still empty
                        if (picked && !titleTouchedRef.current && !title) {
                          const base = picked.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");
                          setTitle(base);
                          setAutoTitle(true);
                        }
                      }}
                    />
                  </label>
                </div>
              )}

              {error && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/25 rounded-lg px-3 py-2.5 flex items-start gap-2">
                  <span className="text-red-400 mt-0.5">!</span>
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-1">
                <Button variant="outline" size="sm" onClick={handleClose}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleIngest}
                  disabled={loading || !canSubmit}
                  className="shadow-glow-sm gap-2"
                >
                  {loading ? "Submitting…" : "Extract & Build Graph"}
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </DialogContent>
    </Dialog>
  );
}
