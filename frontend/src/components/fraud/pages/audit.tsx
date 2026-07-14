"use client";

import { useState, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { AUDIT_LOGS } from "@/lib/fraud-data";
import { formatDateTime, formatTimeAgo } from "@/lib/fraud-utils";
import { ScrollText, Search, Filter, Download } from "lucide-react";

const ACTION_COLORS: Record<string, string> = {
  "User Login": "text-blue-400 bg-blue-500/10",
  "Rule Created": "text-emerald-400 bg-emerald-500/10",
  "Rule Toggled": "text-amber-400 bg-amber-500/10",
  "Model Promoted": "text-[color:var(--signal)] bg-[color:var(--signal)]/10",
  "Model Archived": "text-muted-foreground bg-muted",
  "Case Status Changed": "text-violet-400 bg-violet-500/10",
  "Note Added": "text-blue-400 bg-blue-500/10",
  "Case Assigned": "text-purple-400 bg-purple-500/10",
  "Transaction Blocked": "text-red-400 bg-red-500/10",
  "Transaction Approved": "text-emerald-400 bg-emerald-500/10",
  "Copilot Query": "text-[color:var(--ml)] bg-[color:var(--ml)]/10",
  "Export Generated": "text-muted-foreground bg-muted",
};

export function AuditPage() {
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [selected, setSelected] = useState<number | null>(null);

  const actions = useMemo(() => ["all", ...new Set(AUDIT_LOGS.map((l) => l.action))], []);

  const filtered = useMemo(() => {
    return AUDIT_LOGS.filter((l) => {
      if (actionFilter !== "all" && l.action !== actionFilter) return false;
      if (search) {
        const s = search.toLowerCase();
        return (
          l.username.toLowerCase().includes(s) ||
          l.action.toLowerCase().includes(s) ||
          l.entity_type.toLowerCase().includes(s) ||
          (l.entity_id ?? "").toLowerCase().includes(s)
        );
      }
      return true;
    }).sort((a, b) => +new Date(b.timestamp) - +new Date(a.timestamp));
  }, [search, actionFilter]);

  const selectedLog = selected ? filtered.find((l) => l.id === selected) : null;

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_400px]">
      <div className="space-y-4">
        {/* Filter bar */}
        <Card className="p-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search by user, action, entity…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-8 w-full rounded-md border border-input bg-muted/50 pl-9 pr-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <Filter className="h-3.5 w-3.5 text-muted-foreground" />
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="h-8 rounded-md border border-input bg-muted/50 px-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                {actions.map((a) => (
                  <option key={a} value={a}>{a === "all" ? "All actions" : a}</option>
                ))}
              </select>
            </div>
            <button className="flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-xs text-muted-foreground hover:text-foreground transition">
              <Download className="h-3 w-3" />
              Export
            </button>
            <div className="text-xs text-muted-foreground">
              <span className="font-mono text-foreground tabular">{filtered.length}</span> entries
            </div>
          </div>
        </Card>

        {/* Log list */}
        <Card className="overflow-hidden p-0">
          <div className="scroll-thin max-h-[calc(100vh-260px)] overflow-y-auto">
            {filtered.map((log) => {
              const colorClass = ACTION_COLORS[log.action] ?? "text-muted-foreground bg-muted";
              const isSelected = selected === log.id;
              return (
                <button
                  key={log.id}
                  onClick={() => setSelected(log.id)}
                  className={cn(
                    "flex w-full items-start gap-3 border-b border-border/40 p-3 text-left transition-colors",
                    isSelected ? "bg-primary/5" : "hover:bg-muted/30"
                  )}
                >
                  <div className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-md", colorClass)}>
                    <ScrollText className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold">{log.action}</span>
                      <span className="text-[10px] text-muted-foreground">·</span>
                      <span className="font-mono text-[10px] text-muted-foreground">@{log.username}</span>
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                      <span className="font-mono">{log.entity_type}</span>
                      {log.entity_id && <span className="font-mono">#{log.entity_id}</span>}
                      <span>·</span>
                      <span className="font-mono">{log.ip_address}</span>
                    </div>
                  </div>
                  <span className="shrink-0 text-[10px] text-muted-foreground tabular">
                    {formatTimeAgo(log.timestamp)}
                  </span>
                </button>
              );
            })}
            {filtered.length === 0 && (
              <div className="p-12 text-center text-xs text-muted-foreground">
                No audit log entries match the filters.
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Detail panel */}
      <div className="hidden xl:block">
        {selectedLog ? (
          <Card className="p-5 space-y-4">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Action</div>
              <div className="mt-0.5 text-sm font-semibold">{selectedLog.action}</div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Actor</div>
                <div className="mt-0.5 font-mono">@{selectedLog.username}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">IP Address</div>
                <div className="mt-0.5 font-mono">{selectedLog.ip_address}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Entity Type</div>
                <div className="mt-0.5 font-mono">{selectedLog.entity_type}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Entity ID</div>
                <div className="mt-0.5 font-mono">{selectedLog.entity_id ?? "—"}</div>
              </div>
              <div className="col-span-2">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Timestamp</div>
                <div className="mt-0.5 font-mono tabular">{formatDateTime(selectedLog.timestamp)}</div>
              </div>
            </div>

            {selectedLog.reason && (
              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Reason</div>
                <div className="mt-0.5 rounded-md border border-border/60 p-2.5 text-xs">{selectedLog.reason}</div>
              </div>
            )}

            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Changes</div>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-md border border-red-500/20 bg-red-500/5 p-2.5">
                  <div className="text-[9px] uppercase font-semibold text-red-400 mb-1">Previous</div>
                  <pre className="text-[10px] font-mono whitespace-pre-wrap break-all">
                    {selectedLog.old_value ? JSON.stringify(selectedLog.old_value, null, 2) : "—"}
                  </pre>
                </div>
                <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2.5">
                  <div className="text-[9px] uppercase font-semibold text-emerald-400 mb-1">New</div>
                  <pre className="text-[10px] font-mono whitespace-pre-wrap break-all">
                    {selectedLog.new_value ? JSON.stringify(selectedLog.new_value, null, 2) : "—"}
                  </pre>
                </div>
              </div>
            </div>
          </Card>
        ) : (
          <Card className="flex h-full min-h-[400px] flex-col items-center justify-center p-8 text-center">
            <ScrollText className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-sm font-medium text-muted-foreground">Select an entry</p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              Click any row to view the full audit record including actor, IP, reason, and value diff.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
