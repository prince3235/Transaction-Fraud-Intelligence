"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { RiskBadge, StatusBadge } from "@/components/fraud/risk-badge";
import { RiskBar } from "@/components/fraud/risk-bar";
import { ALERTS } from "@/lib/fraud-data";
import type { PredictionLog, RiskLevel, TxStatus } from "@/lib/fraud-data";
import { formatCompactCurrency, formatDateTime, formatProbability, formatTimeAgo } from "@/lib/fraud-utils";
import { Filter, ArrowUpDown, X, Activity, Check, Ban, AlertTriangle } from "lucide-react";

type SortKey = "created_at" | "amount" | "risk_score";

export function AlertsPage() {
  const [riskFilter, setRiskFilter] = useState<Set<RiskLevel>>(new Set(["CRITICAL", "HIGH", "MEDIUM"]));
  const [statusFilter, setStatusFilter] = useState<Set<TxStatus>>(new Set(["PENDING_REVIEW", "ESCALATED"]));
  const [overrideOnly, setOverrideOnly] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("risk_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [selected, setSelected] = useState<PredictionLog | null>(null);

  const filtered = useMemo(() => {
    let list = ALERTS.filter((a) => riskFilter.has(a.final_risk_level));
    if (statusFilter.size > 0) list = list.filter((a) => statusFilter.has(a.status));
    if (overrideOnly) list = list.filter((a) => a.policy_override_applied);
    list = list.slice().sort((a, b) => {
      let cmp = 0;
      if (sortKey === "created_at") cmp = +new Date(a.created_at) - +new Date(b.created_at);
      else if (sortKey === "amount") cmp = a.transaction.amount - b.transaction.amount;
      else cmp = a.final_risk_score - b.final_risk_score;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [riskFilter, statusFilter, overrideOnly, sortKey, sortDir]);

  const toggleRisk = (r: RiskLevel) => {
    setRiskFilter((p) => {
      const next = new Set(p);
      if (next.has(r)) next.delete(r);
      else next.add(r);
      return next;
    });
  };
  const toggleStatus = (s: TxStatus) => {
    setStatusFilter((p) => {
      const next = new Set(p);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };
  const toggleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(k);
      setSortDir("desc");
    }
  };

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_400px]">
      {/* Left: filters + table */}
      <div className="space-y-4">
        {/* Filter bar */}
        <Card className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Filter className="h-3.5 w-3.5" />
              <span>Filters:</span>
            </div>
            {/* Risk */}
            <div className="flex items-center gap-1">
              {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as RiskLevel[]).map((r) => (
                <button
                  key={r}
                  onClick={() => toggleRisk(r)}
                  className={cn(
                    "rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wider transition",
                    riskFilter.has(r)
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : "border-border bg-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
            <span className="h-4 w-px bg-border" />
            {/* Status */}
            <div className="flex items-center gap-1">
              {(["PENDING_REVIEW", "ESCALATED", "APPROVED", "BLOCKED"] as TxStatus[]).map((s) => (
                <button
                  key={s}
                  onClick={() => toggleStatus(s)}
                  className={cn(
                    "rounded-md border px-2 py-1 text-[10px] font-medium transition",
                    statusFilter.has(s)
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : "border-border bg-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  {s.replace(/_/g, " ")}
                </button>
              ))}
            </div>
            <span className="h-4 w-px bg-border" />
            <button
              onClick={() => setOverrideOnly((p) => !p)}
              className={cn(
                "flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-medium transition",
                overrideOnly
                  ? "border-violet-500/40 bg-violet-500/10 text-violet-300"
                  : "border-border bg-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              Policy overrides only
            </button>
            <div className="ml-auto text-xs text-muted-foreground">
              Showing <span className="font-mono text-foreground tabular">{filtered.length}</span> alerts
            </div>
          </div>
        </Card>

        {/* Table */}
        <Card className="overflow-hidden p-0">
          <div className="scroll-thin max-h-[calc(100vh-280px)] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10 bg-card/95 backdrop-blur">
                <tr className="border-b border-border">
                  <Th onClick={() => toggleSort("created_at")} active={sortKey === "created_at"} dir={sortDir}>
                    Time
                  </Th>
                  <Th>Type</Th>
                  <Th>Parties</Th>
                  <Th onClick={() => toggleSort("amount")} active={sortKey === "amount"} dir={sortDir} align="right">
                    Amount
                  </Th>
                  <Th onClick={() => toggleSort("risk_score")} active={sortKey === "risk_score"} dir={sortDir}>
                    Risk Score
                  </Th>
                  <Th>Level</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr
                    key={a.id}
                    onClick={() => setSelected(a)}
                    className={cn(
                      "border-b border-border/40 cursor-pointer transition-colors",
                      selected?.id === a.id ? "bg-primary/5" : "hover:bg-muted/40"
                    )}
                  >
                    <td className="px-3 py-2.5 text-[10px] text-muted-foreground tabular whitespace-nowrap">
                      {formatTimeAgo(a.created_at)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="font-mono text-[11px] font-medium">{a.transaction.type}</span>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-1.5 text-[11px]">
                        <span className="font-mono text-muted-foreground">{a.transaction.nameOrig}</span>
                        <span className="text-muted-foreground/40">→</span>
                        <span className="font-mono text-muted-foreground">{a.transaction.nameDest}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono tabular">
                      {formatCompactCurrency(a.transaction.amount)}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="w-7 font-mono tabular text-right">{a.final_risk_score}</span>
                        <div className="w-16">
                          <RiskBar score={a.final_risk_score} showScale={false} />
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <RiskBadge level={a.final_risk_level} size="sm" />
                    </td>
                    <td className="px-3 py-2.5">
                      <StatusBadge status={a.status} size="sm" />
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-3 py-12 text-center text-muted-foreground">
                      No alerts match the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Right: detail panel */}
      <div className="hidden xl:block">
        {selected ? <AlertDetail alert={selected} onClose={() => setSelected(null)} /> : (
          <Card className="flex h-full min-h-[400px] flex-col items-center justify-center p-8 text-center">
            <Activity className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-sm font-medium text-muted-foreground">Select an alert</p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              Click any row to view transaction details, ML explanation, and policy reasons.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}

function Th({
  children,
  onClick,
  active,
  dir,
  align = "left",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  active?: boolean;
  dir?: "asc" | "desc";
  align?: "left" | "right";
}) {
  return (
    <th
      onClick={onClick}
      className={cn(
        "px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground",
        onClick && "cursor-pointer hover:text-foreground",
        align === "right" ? "text-right" : "text-left"
      )}
    >
      <span className={cn("inline-flex items-center gap-1", align === "right" && "flex-row-reverse")}>
        {children}
        {onClick && (
          <ArrowUpDown className={cn("h-3 w-3", active ? "text-primary" : "text-muted-foreground/50")} />
        )}
      </span>
    </th>
  );
}

function AlertDetail({ alert, onClose }: { alert: PredictionLog; onClose: () => void }) {
  return (
    <Card className="flex h-[calc(100vh-200px)] flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-border p-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">#{alert.id}</span>
            <RiskBadge level={alert.final_risk_level} size="sm" />
            <StatusBadge status={alert.status} size="sm" />
          </div>
          <h3 className="mt-1.5 font-mono text-sm font-semibold">
            {alert.transaction.type} · {formatCompactCurrency(alert.transaction.amount)}
          </h3>
          <p className="text-[10px] text-muted-foreground">{formatDateTime(alert.created_at)}</p>
        </div>
        <button
          onClick={onClose}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="scroll-thin flex-1 overflow-y-auto p-4 space-y-4">
        {/* Parties */}
        <section>
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Parties</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-md border border-border/60 p-2.5">
              <div className="text-[9px] uppercase text-muted-foreground">Sender</div>
              <div className="mt-0.5 font-mono font-medium">{alert.transaction.nameOrig}</div>
              <div className="mt-1 space-y-0.5 text-[10px] text-muted-foreground tabular">
                <div>Old bal: {formatCompactCurrency(alert.transaction.oldbalanceOrg)}</div>
                <div>New bal: {formatCompactCurrency(alert.transaction.newbalanceOrig)}</div>
              </div>
            </div>
            <div className="rounded-md border border-border/60 p-2.5">
              <div className="text-[9px] uppercase text-muted-foreground">Recipient</div>
              <div className="mt-0.5 font-mono font-medium">{alert.transaction.nameDest}</div>
              <div className="mt-1 space-y-0.5 text-[10px] text-muted-foreground tabular">
                <div>Old bal: {formatCompactCurrency(alert.transaction.oldbalanceDest)}</div>
                <div>New bal: {formatCompactCurrency(alert.transaction.newbalanceDest)}</div>
              </div>
            </div>
          </div>
        </section>

        {/* ML score */}
        <section>
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">ML Inference</h4>
          <div className="rounded-md border border-border/60 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Probability</span>
              <span className="font-mono tabular font-semibold text-[color:var(--signal)]">
                {formatProbability(alert.ml_probability)}
              </span>
            </div>
            <div className="mt-2">
              <RiskBar score={alert.final_risk_score} />
            </div>
            <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
              <span>ML base: <span className="font-mono text-foreground">{alert.ml_risk_level}</span> ({alert.ml_risk_score})</span>
              <span>Final: <span className="font-mono text-foreground">{alert.final_risk_level}</span> ({alert.final_risk_score})</span>
            </div>
          </div>
        </section>

        {/* Policy reasons */}
        <section>
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Policy & Rules ({alert.policy_reasons.length})
          </h4>
          {alert.policy_reasons.length === 0 ? (
            <p className="rounded-md border border-border/60 p-3 text-xs text-muted-foreground">
              No policy overrides applied — ML score used as-is.
            </p>
          ) : (
            <div className="space-y-1.5">
              {alert.policy_reasons.map((r, i) => (
                <div key={i} className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2.5 text-xs">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-400" />
                    <span>{r}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Signal count */}
        <section>
          <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Signals</h4>
          <div className="flex items-center gap-1">
            {Array.from({ length: 6 }, (_, i) => (
              <div
                key={i}
                className={cn(
                  "h-2 flex-1 rounded-full",
                  i < alert.suspicious_signal_count ? "bg-[color:var(--risk-critical)]" : "bg-muted"
                )}
              />
            ))}
            <span className="ml-2 font-mono text-xs tabular">
              {alert.suspicious_signal_count}/6
            </span>
          </div>
        </section>
      </div>

      {/* Actions */}
      <div className="border-t border-border p-3 flex gap-2">
        <button className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-emerald-500/15 px-3 py-2 text-xs font-medium text-emerald-400 hover:bg-emerald-500/25 transition">
          <Check className="h-3.5 w-3.5" />
          Approve
        </button>
        <button className="flex-1 flex items-center justify-center gap-1.5 rounded-md bg-red-500/15 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/25 transition">
          <Ban className="h-3.5 w-3.5" />
          Block
        </button>
      </div>
    </Card>
  );
}
