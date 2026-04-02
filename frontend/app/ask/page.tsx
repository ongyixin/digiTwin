"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Terminal } from "lucide-react";
import { api } from "@/lib/api";
import { useInspector } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { PulseIndicator } from "@/components/shared/PulseIndicator";
import type { Citation, QueryResponse } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  error?: boolean;
}

const SUGGESTED = [
  "Why did we choose the April 15 launch date?",
  "What assumptions is the beta launch decision based on?",
  "Which open tasks might block launch?",
  "Who needs to approve the launch decision?",
];

function CitationDetail({ citation }: { citation: Citation }) {
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground font-mono">{citation.label} · {citation.id}</div>
      <div className="text-sm font-medium text-foreground">{citation.title}</div>
      {citation.excerpt && (
        <blockquote className="border-l-2 border-primary/50 pl-3 text-xs text-muted-foreground italic leading-relaxed">
          {citation.excerpt}
        </blockquote>
      )}
    </div>
  );
}

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [userId] = useState("alex");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { openInspector } = useInspector();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.query(question, userId) as QueryResponse;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, citations: res.citations || [] },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: e instanceof Error ? e.message : "Unknown error", error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  return (
    <div className="flex flex-col h-screen px-6 pb-6 pt-4 max-w-4xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="flex items-center justify-between gap-3 mb-4 shrink-0"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
            <Terminal className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-foreground">Ask the Twin</h1>
            <p className="text-xs text-muted-foreground">Graph-grounded intelligence with decision lineage</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <PulseIndicator color="emerald" />
          <span>Connected to knowledge graph</span>
        </div>
      </motion.div>
      <div className="gradient-rule mb-4 shrink-0" />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 min-h-0">
        <AnimatePresence initial={false}>
          {messages.length === 0 && (
            <motion.div
              key="suggestions"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {/* Decorative graph motif */}
              <svg width="80" height="50" viewBox="0 0 80 50" className="opacity-15 mx-auto">
                <circle cx="40" cy="25" r="6" stroke="hsl(var(--primary))" strokeWidth="1.5" fill="none" />
                <circle cx="12" cy="10" r="4" stroke="hsl(var(--primary))" strokeWidth="1" fill="none" />
                <circle cx="68" cy="10" r="4" stroke="hsl(var(--primary))" strokeWidth="1" fill="none" />
                <circle cx="12" cy="40" r="4" stroke="hsl(var(--border))" strokeWidth="1" fill="none" />
                <circle cx="68" cy="40" r="4" stroke="hsl(var(--border))" strokeWidth="1" fill="none" />
                <line x1="15" y1="12" x2="35" y2="21" stroke="hsl(var(--primary))" strokeWidth="0.8" />
                <line x1="65" y1="12" x2="45" y2="21" stroke="hsl(var(--primary))" strokeWidth="0.8" />
                <line x1="15" y1="38" x2="35" y2="28" stroke="hsl(var(--border))" strokeWidth="0.8" />
                <line x1="65" y1="38" x2="45" y2="28" stroke="hsl(var(--border))" strokeWidth="0.8" />
              </svg>
              <p className="text-xs text-muted-foreground uppercase tracking-[0.15em] font-semibold text-center">
                Start an investigation
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SUGGESTED.map((s, i) => (
                  <motion.button
                    key={s}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05, duration: 0.18 }}
                    onClick={() => send(s)}
                    className="text-left p-4 rounded-xl bg-card border border-border hover:border-primary/40 transition-all group"
                    style={{ backgroundImage: "none" }}
                  >
                    <div className="text-xs font-mono text-primary mb-1.5 opacity-50 group-hover:opacity-100 transition-opacity">
                      &gt;_<span className="animate-pulse-dot inline-block w-1.5 h-3 bg-primary ml-0.5 align-middle opacity-80" />
                    </div>
                    <div className="text-sm text-foreground leading-relaxed">{s}</div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "user" ? (
                <div className="max-w-xl bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-4 py-2.5 text-sm shadow-glow-sm">
                  {msg.content}
                </div>
              ) : (
                <div
                  className={`w-full rounded-2xl rounded-bl-sm px-5 py-4 space-y-3 border ${
                    msg.error
                      ? "bg-red-500/10 border-red-500/30"
                      : "bg-card border-border"
                  }`}
                >
                  <div
                    className={`text-sm leading-relaxed whitespace-pre-wrap ${
                      msg.error ? "text-red-400" : "text-foreground"
                    }`}
                  >
                    {msg.content}
                  </div>
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2.5 border-t border-border/50">
                      <div className="text-xs text-muted-foreground uppercase tracking-[0.14em] font-semibold mb-2">
                        Evidence Basis
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.citations.map((c) => (
                          <button
                            key={c.id}
                            onClick={() => openInspector(c.title, <CitationDetail citation={c} />)}
                            className="text-xs bg-muted/60 hover:bg-primary/15 hover:text-primary border border-border hover:border-primary/40 rounded-md px-2 py-0.5 transition-colors font-mono flex items-center gap-1"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-primary/50 shrink-0" />
                            {c.label}: {c.title}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          ))}

          {loading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex justify-start"
            >
              <div className="bg-card border border-border rounded-2xl rounded-bl-sm px-5 py-3 text-xs text-muted-foreground flex items-center gap-2">
                <div className="h-1 w-24 rounded animate-shimmer" />
                Searching the decision graph…
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 pt-3 border-t border-border">
        <form
          onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="flex gap-2 items-end"
        >
          <textarea
            ref={inputRef}
            className="flex-1 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary/50 font-mono text-foreground placeholder:text-muted-foreground/50 min-h-[44px] max-h-32 border border-border transition-colors"
            style={{ background: "hsl(var(--input))", boxShadow: "inset 0 1px 3px hsl(0 0% 0% / 0.15)" }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about any decision…"
            disabled={loading}
            rows={1}
          />
          <Button
            type="submit"
            size="icon"
            disabled={loading || !input.trim()}
            className={`h-11 w-11 shrink-0 transition-shadow ${input.trim() ? "shadow-glow-sm" : ""}`}
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
        <div className="text-xs text-muted-foreground/50 mt-1.5 text-right">
          Enter to send · Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
