"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { RiskBadge, StatusBadge } from "@/components/fraud/risk-badge";
import { ShapWaterfall } from "@/components/fraud/shap-waterfall";
import { CopilotChat } from "@/components/fraud/copilot-chat";
import { CASES, SHAP_CONTRIBUTORS } from "@/lib/fraud-data";
import type { FraudCase } from "@/lib/fraud-data";
import { formatCompactCurrency, formatDateTime, formatTimeAgo } from "@/lib/fraud-utils";
import { FolderKanban, Plus, MessageSquare, Activity, Clock, User, ArrowLeft, Send } from "lucide-react";

type View = "list" | "detail";

export function CasesPage() {
  const [view, setView] = useState<View>("list");
  const [selected, setSelected] = useState<FraudCase | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const filtered = CASES.filter((c) => {
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    if (search && !c.title.toLowerCase().includes(search.toLowerCase()) && !c.case_id.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const openCase = (c: FraudCase) => {
    setSelected(c);
    setView("detail");
  };
  const backToList = () => {
    setView("list");
    setSelected(null);
  };

  if (view === "detail" && selected) {
    return <CaseDetail caseData={selected} onBack={backToList} />;
  }

  return (
    <div className="space-y-4">
      {/* Filter row */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          {["all", "OPEN", "INVESTIGATING", "ESCALATED", "RESOLVED"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "rounded-md border px-2.5 py-1 text-[11px] font-medium transition",
                statusFilter === s
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-border bg-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {s === "all" ? "All" : s.charAt(0) + s.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Search by title or case ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 flex-1 min-w-[200px] rounded-md border border-input bg-muted/50 px-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
        <div className="text-xs text-muted-foreground">
          <span className="font-mono text-foreground tabular">{filtered.length}</span> cases
        </div>
      </div>

      {/* Cases grid */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {filtered.map((c) => (
          <Card
            key={c.id}
            className="p-4 cursor-pointer hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 transition-all"
            onClick={() => openCase(c)}
          >
            {/* Top: case ID + status + priority */}
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-muted-foreground">{c.case_id}</span>
              <div className="flex items-center gap-1.5">
                <PriorityBadge priority={c.priority} />
                <StatusBadge status={c.status} size="sm" />
              </div>
            </div>

            {/* Title */}
            <h3 className="mt-2 text-sm font-medium leading-snug line-clamp-2">{c.title}</h3>
            <p className="mt-1 text-[11px] text-muted-foreground line-clamp-2">{c.description}</p>

            {/* Footer: risk, amount, time, assignee */}
            <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-3">
              <div className="flex items-center gap-2">
                <RiskBadge level={c.risk_level} size="sm" />
                <span className="font-mono text-xs tabular">{formatCompactCurrency(c.amount)}</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                {c.assigned_to && (
                  <span className="flex items-center gap-1">
                    <User className="h-2.5 w-2.5" />
                    {c.assigned_to}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Clock className="h-2.5 w-2.5" />
                  {formatTimeAgo(c.created_at)}
                </span>
              </div>
            </div>
          </Card>
        ))}
        {filtered.length === 0 && (
          <div className="col-span-full">
            <Card className="flex flex-col items-center justify-center p-12 text-center">
              <FolderKanban className="mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">No cases match the current filters.</p>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

function PriorityBadge({ priority }: { priority: "P1" | "P2" | "P3" }) {
  const colors = {
    P1: "bg-red-500/15 text-red-400 border-red-500/30",
    P2: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    P3: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  };
  return (
    <span className={cn("rounded border px-1.5 py-0.5 text-[9px] font-bold", colors[priority])}>
      {priority}
    </span>
  );
}

function CaseDetail({ caseData, onBack }: { caseData: FraudCase; onBack: () => void }) {
  const [tab, setTab] = useState<"overview" | "notes" | "timeline" | "xai" | "copilot">("overview");
  const [newNote, setNewNote] = useState("");
  const [notes, setNotes] = useState(caseData.notes);

  const addNote = () => {
    if (!newNote.trim()) return;
    setNotes((p) => [
      ...p,
      {
        id: p.length + 1,
        author: "A.Patel",
        content: newNote.trim(),
        timestamp: new Date().toISOString(),
      },
    ]);
    setNewNote("");
  };

  return (
    <div className="space-y-4">
      {/* Breadcrumb / header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-muted hover:text-foreground transition"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-muted-foreground">{caseData.case_id}</span>
            <PriorityBadge priority={caseData.priority} />
            <StatusBadge status={caseData.status} size="sm" />
            <RiskBadge level={caseData.risk_level} size="sm" />
          </div>
          <h2 className="mt-1 truncate text-base font-semibold">{caseData.title}</h2>
        </div>
        <div className="text-right">
          <div className="font-mono text-lg tabular">{formatCompactCurrency(caseData.amount)}</div>
          <div className="text-[10px] text-muted-foreground">at risk</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border">
        {([
          ["overview", "Overview"],
          ["notes", `Notes (${notes.length})`],
          ["timeline", "Timeline"],
          ["xai", "XAI · SHAP"],
          ["copilot", "AI Copilot"],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={cn(
              "relative -mb-px px-3 py-2 text-xs font-medium transition",
              tab === k
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {label}
            {tab === k && <span className="absolute inset-x-0 bottom-0 h-0.5 bg-primary" />}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          {tab === "overview" && (
            <Card className="p-5 space-y-4">
              <section>
                <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Description</h3>
                <p className="text-sm leading-relaxed">{caseData.description}</p>
              </section>
              <section className="grid grid-cols-2 gap-3 border-t border-border/60 pt-4">
                <DetailItem label="Created" value={formatDateTime(caseData.created_at)} icon={Clock} />
                <DetailItem label="Updated" value={formatDateTime(caseData.updated_at)} icon={Activity} />
                <DetailItem label="Assigned to" value={caseData.assigned_to ?? "Unassigned"} icon={User} />
                <DetailItem label="Resolved" value={caseData.resolved_at ? formatDateTime(caseData.resolved_at) : "—"} icon={Activity} />
              </section>
            </Card>
          )}

          {tab === "notes" && (
            <Card className="p-5">
              <div className="space-y-3 mb-4">
                {notes.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-8">No notes yet.</p>
                )}
                {notes.map((n) => (
                  <div key={n.id} className="rounded-md border border-border/60 p-3">
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1.5">
                      <span className="flex items-center gap-1.5">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-500/20 text-[9px] font-semibold text-violet-300">
                          {n.author.slice(0, 2).toUpperCase()}
                        </span>
                        <span className="font-medium text-foreground">@{n.author}</span>
                      </span>
                      <span>{formatTimeAgo(n.timestamp)}</span>
                    </div>
                    <p className="text-xs leading-relaxed">{n.content}</p>
                  </div>
                ))}
              </div>
              <div className="border-t border-border/60 pt-3">
                <div className="flex gap-2">
                  <textarea
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="Add an investigation note…"
                    rows={2}
                    className="flex-1 rounded-md border border-input bg-muted/50 px-3 py-2 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                  />
                  <button
                    onClick={addNote}
                    className="self-end rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition"
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </Card>
          )}

          {tab === "timeline" && (
            <Card className="p-5">
              <div className="relative pl-6">
                <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border" />
                {caseData.timeline.map((ev) => (
                  <div key={ev.id} className="relative mb-5 last:mb-0">
                    <div className="absolute -left-[22px] top-1 h-3 w-3 rounded-full border-2 border-background bg-primary" />
                    <div className="text-[10px] text-muted-foreground">
                      {formatDateTime(ev.timestamp)} · <span className="font-mono">@{ev.actor}</span>
                    </div>
                    <div className="mt-0.5 text-xs font-semibold">{ev.action}</div>
                    {ev.note && <div className="mt-0.5 text-[11px] text-muted-foreground">{ev.note}</div>}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {tab === "xai" && <ShapWaterfall contributors={SHAP_CONTRIBUTORS} />}
        </div>

        {/* Right rail: copilot or case info */}
        <div className="xl:col-span-1">
          {tab === "copilot" ? (
            <CopilotChat caseId={caseData.case_id} />
          ) : (
            <Card className="p-4 space-y-3">
              <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Case Summary</h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between"><span className="text-muted-foreground">Case ID</span><span className="font-mono">{caseData.case_id}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Linked log</span><span className="font-mono">#{caseData.prediction_log_id}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Priority</span><PriorityBadge priority={caseData.priority} /></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Risk</span><RiskBadge level={caseData.risk_level} size="sm" /></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Amount</span><span className="font-mono tabular">{formatCompactCurrency(caseData.amount)}</span></div>
              </div>
              <div className="border-t border-border/60 pt-3">
                <button
                  onClick={() => setTab("copilot")}
                  className="flex w-full items-center justify-center gap-2 rounded-md bg-[color:var(--ml)]/15 px-3 py-2 text-xs font-medium text-[color:var(--ml)] hover:bg-[color:var(--ml)]/25 transition"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  Ask AI Copilot
                </button>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailItem({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Clock }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <div className="mt-1 font-mono text-xs tabular">{value}</div>
    </div>
  );
}
