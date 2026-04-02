"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageCircle,
  X,
  Send,
  Mic,
  MicOff,
  Bot,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useSpeechRecognition } from "@/lib/hooks";
import type { Citation, QueryResponse } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  error?: boolean;
}

const SUGGESTED_QUESTIONS = [
  "What decisions are pending approval?",
  "Which actions are currently blocked?",
  "How do I ingest a new document?",
  "How do I navigate the dependency map?",
  "Show me recent agent activity",
  "How do I check user permissions?",
];

export function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSpeechResult = useCallback((transcript: string) => {
    setInput(transcript);
  }, []);

  const { isListening, isSupported, startListening, stopListening } =
    useSpeechRecognition(handleSpeechResult);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => textareaRef.current?.focus(), 150);
    }
  }, [isOpen]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    stopListening();
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = (await api.chatbot(question, "alex")) as QueryResponse;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations || [],
        },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            e instanceof Error
              ? e.message
              : "Something went wrong. Please try again.",
          error: true,
        },
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

  function toggleMic() {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* Chat panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="chatbot-panel"
            initial={{ opacity: 0, scale: 0.92, y: 16, originX: 1, originY: 1 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 16 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className="w-[380px] h-[520px] rounded-2xl border border-border bg-background/95 backdrop-blur-xl shadow-2xl flex flex-col overflow-hidden"
            style={{
              boxShadow:
                "0 0 0 1px hsl(var(--border)), 0 24px 48px -12px hsl(0 0% 0% / 0.7), 0 0 32px -8px hsl(var(--primary) / 0.15)",
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0 bg-card/50">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
                  <Bot className="w-3.5 h-3.5 text-primary" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground leading-none">
                    digiTwin Assistant
                  </div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">
                    {loading ? (
                      <span className="text-amber-400 animate-pulse">Thinking…</span>
                    ) : (
                      "Ask anything about your data or dashboard"
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md hover:bg-muted"
                aria-label="Close chat"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
              <AnimatePresence initial={false}>
                {messages.length === 0 && (
                  <motion.div
                    key="suggestions"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="space-y-3"
                  >
                    <p className="text-[10px] text-muted-foreground uppercase tracking-[0.14em] font-semibold text-center pt-1">
                      Quick questions
                    </p>
                    <div className="grid grid-cols-1 gap-1.5">
                      {SUGGESTED_QUESTIONS.map((q, i) => (
                        <motion.button
                          key={q}
                          initial={{ opacity: 0, y: 4 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.04, duration: 0.15 }}
                          onClick={() => send(q)}
                          className="text-left px-3 py-2 rounded-lg bg-muted/40 hover:bg-muted border border-border hover:border-primary/30 text-xs text-foreground/80 hover:text-foreground transition-all"
                        >
                          {q}
                        </motion.button>
                      ))}
                    </div>
                  </motion.div>
                )}

                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {msg.role === "user" ? (
                      <div className="max-w-[85%] bg-primary text-primary-foreground rounded-xl rounded-br-sm px-3 py-2 text-sm shadow-glow-sm">
                        {msg.content}
                      </div>
                    ) : (
                      <div
                        className={`max-w-[92%] rounded-xl rounded-bl-sm px-3 py-2.5 space-y-2 border ${
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
                          <div className="pt-1.5 border-t border-border/50 flex flex-wrap gap-1">
                            {msg.citations.map((c) => (
                              <span
                                key={c.id}
                                className="text-[10px] bg-muted/60 border border-border rounded px-1.5 py-0.5 font-mono text-muted-foreground flex items-center gap-1"
                                title={c.excerpt || c.title}
                              >
                                <span className="w-1 h-1 rounded-full bg-primary/50 shrink-0" />
                                {c.label}: {c.title}
                              </span>
                            ))}
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
                    <div className="bg-card border border-border rounded-xl rounded-bl-sm px-3 py-2.5 text-xs text-muted-foreground flex items-center gap-2">
                      <span className="flex gap-0.5">
                        {[0, 1, 2].map((n) => (
                          <span
                            key={n}
                            className="w-1.5 h-1.5 rounded-full bg-primary/50 animate-bounce"
                            style={{ animationDelay: `${n * 0.12}s` }}
                          />
                        ))}
                      </span>
                      Searching the knowledge graph…
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={bottomRef} />
            </div>

            {/* Input bar */}
            <div className="shrink-0 px-3 py-3 border-t border-border bg-card/30">
              <div className="flex gap-1.5 items-end">
                <div className="relative flex-1">
                  <textarea
                    ref={textareaRef}
                    className="w-full rounded-xl px-3 py-2 pr-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary/50 font-sans text-foreground placeholder:text-muted-foreground/50 min-h-[38px] max-h-28 border border-border transition-colors"
                    style={{
                      background: "hsl(var(--input))",
                      boxShadow: "inset 0 1px 3px hsl(0 0% 0% / 0.15)",
                    }}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      isListening ? "Listening…" : "Ask a question…"
                    }
                    disabled={loading}
                    rows={1}
                  />
                  {isListening && (
                    <span className="absolute right-2.5 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  )}
                </div>

                {isSupported && (
                  <Button
                    type="button"
                    size="icon"
                    variant={isListening ? "destructive" : "outline"}
                    onClick={toggleMic}
                    disabled={loading}
                    className="h-[38px] w-[38px] shrink-0"
                    title={isListening ? "Stop listening" : "Speak your question"}
                    aria-label={isListening ? "Stop listening" : "Speak"}
                  >
                    {isListening ? (
                      <MicOff className="w-3.5 h-3.5" />
                    ) : (
                      <Mic className="w-3.5 h-3.5" />
                    )}
                  </Button>
                )}

                <Button
                  type="button"
                  size="icon"
                  disabled={loading || !input.trim()}
                  onClick={() => send(input)}
                  className={`h-[38px] w-[38px] shrink-0 transition-shadow ${
                    input.trim() ? "shadow-glow-sm" : ""
                  }`}
                  aria-label="Send message"
                >
                  <Send className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB toggle button */}
      <motion.button
        onClick={() => setIsOpen((v) => !v)}
        aria-label={isOpen ? "Close assistant" : "Open digiTwin Assistant"}
        className="relative w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-glow flex items-center justify-center focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        whileHover={{ scale: 1.07 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
      >
        <AnimatePresence mode="wait" initial={false}>
          {isOpen ? (
            <motion.span
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <X className="w-5 h-5" />
            </motion.span>
          ) : (
            <motion.span
              key="open"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <MessageCircle className="w-5 h-5" />
            </motion.span>
          )}
        </AnimatePresence>

        {/* Unread pulse ring — shown when panel is closed */}
        {!isOpen && messages.length === 0 && (
          <span className="absolute inset-0 rounded-full border-2 border-primary/40 animate-ping opacity-60" />
        )}
      </motion.button>
    </div>
  );
}
