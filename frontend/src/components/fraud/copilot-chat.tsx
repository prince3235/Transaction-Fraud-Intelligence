"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { COPILOT_RESPONSE } from "@/lib/fraud-data";
import { Bot, Send, User, Sparkles, ArrowUpCircle } from "lucide-react";

interface CopilotChatProps {
  caseId: string;
}

interface Msg {
  id: number;
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "Why was this flagged as critical?",
  "Has this customer been flagged before?",
  "What patterns are common in this fraud type?",
  "Recommend escalation?",
];

export function CopilotChat({ caseId }: CopilotChatProps) {
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: 0,
      role: "assistant",
      content: `Hello — I'm the Fraud Copilot for case **${caseId}**. I have access to the transaction details, ML explanation, account history, and active business rules. Ask me anything.`,
    },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = (text: string) => {
    if (!text.trim() || streaming) return;
    const userMsg: Msg = { id: messages.length, role: "user", content: text };
    setMessages((p) => [...p, userMsg]);
    setInput("");
    setStreaming(true);

    // Simulate streaming response
    const fullResponse = COPILOT_RESPONSE;
    const assistantId = messages.length + 1;
    setMessages((p) => [...p, { id: assistantId, role: "assistant", content: "" }]);

    let i = 0;
    const interval = setInterval(() => {
      i += 3;
      const chunk = fullResponse.slice(0, i);
      setMessages((p) =>
        p.map((m) => (m.id === assistantId ? { ...m, content: chunk } : m))
      );
      if (i >= fullResponse.length) {
        clearInterval(interval);
        setStreaming(false);
      }
    }, 20);
  };

  const shouldShowEscalate = messages.some((m) => m.content.includes("[RECOMMEND_ESCALATION]"));

  return (
    <Card className="flex h-[calc(100vh-280px)] min-h-[400px] flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border p-3">
        <div className="relative flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-[color:var(--ml)]/40 to-[color:var(--ml)]/20">
          <Bot className="h-4 w-4 text-[color:var(--ml)]" />
          <Sparkles className="absolute -top-1 -right-1 h-3 w-3 text-amber-400" />
        </div>
        <div className="flex-1">
          <div className="text-xs font-semibold">Fraud Copilot</div>
          <div className="text-[10px] text-muted-foreground">Claude · DB-grounded · Compliance-logged</div>
        </div>
        <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[9px] font-semibold text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Ready
        </span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="scroll-thin flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={cn("flex gap-2.5", m.role === "user" && "flex-row-reverse")}
          >
            <div
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold",
                m.role === "user"
                  ? "bg-primary/15 text-primary"
                  : "bg-[color:var(--ml)]/15 text-[color:var(--ml)]"
              )}
            >
              {m.role === "user" ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
            </div>
            <div
              className={cn(
                "max-w-[80%] rounded-lg px-3 py-2 text-xs leading-relaxed",
                m.role === "user"
                  ? "bg-primary/10 text-foreground"
                  : "bg-muted/60 text-foreground"
              )}
            >
              <FormattedContent content={m.content} />
              {m.role === "assistant" && m.content === "" && (
                <span className="inline-flex gap-0.5">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Suggestion chips */}
      {messages.length <= 2 && (
        <div className="border-t border-border p-2 flex flex-wrap gap-1">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="rounded-full border border-border bg-muted/40 px-2.5 py-1 text-[10px] text-muted-foreground hover:bg-muted hover:text-foreground transition"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Escalate banner */}
      {shouldShowEscalate && (
        <div className="border-t border-border p-2">
          <button className="flex w-full items-center justify-center gap-1.5 rounded-md bg-red-500/15 px-3 py-2 text-xs font-semibold text-red-400 hover:bg-red-500/25 transition">
            <ArrowUpCircle className="h-3.5 w-3.5" />
            Escalate to L2 review
          </button>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-border p-2.5">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder="Ask about this transaction…"
            disabled={streaming}
            className="flex-1 rounded-md border border-input bg-muted/50 px-3 py-2 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
          />
          <button
            onClick={() => send(input)}
            disabled={streaming || !input.trim()}
            className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </Card>
  );
}

/** Lightweight markdown-ish formatter: bold + numbered lists + brackets. */
function FormattedContent({ content }: { content: string }) {
  // Strip the sentinel token from visible output
  const clean = content.replace(/\[RECOMMEND_ESCALATION\]/g, "").trim();
  // Split by lines, render bold + lists
  const lines = clean.split("\n");
  return (
    <div className="space-y-1.5">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />;
        // Bold: **text**
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        const rendered = parts.map((p, j) =>
          p.startsWith("**") && p.endsWith("**") ? (
            <strong key={j} className="font-semibold">{p.slice(2, -2)}</strong>
          ) : (
            <span key={j}>{p}</span>
          )
        );
        // Numbered list item
        if (/^\d+\.\s/.test(line)) {
          return (
            <div key={i} className="flex gap-2">
              <span className="font-mono text-[color:var(--ml)]">{line.match(/^\d+\./)?.[0]}</span>
              <span>{rendered.slice(1)}</span>
            </div>
          );
        }
        return <p key={i} className="leading-relaxed">{rendered}</p>;
      })}
    </div>
  );
}
