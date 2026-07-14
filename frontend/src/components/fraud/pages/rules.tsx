"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { RULES } from "@/lib/fraud-data";
import type { BusinessRule } from "@/lib/fraud-data";
import { RiskBadge } from "@/components/fraud/risk-badge";
import { formatNumber, formatTimeAgo } from "@/lib/fraud-utils";
import { Plus, Search, Settings2, Zap, Power, X } from "lucide-react";

const TYPE_LABELS: Record<BusinessRule["rule_type"], string> = {
  AMOUNT: "Amount",
  VELOCITY: "Velocity",
  PATTERN: "Pattern",
  GEO: "Geography",
  BALANCE: "Balance",
};

export function RulesPage() {
  const [rules, setRules] = useState<BusinessRule[]>(RULES);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const filtered = rules.filter(
    (r) =>
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.description.toLowerCase().includes(search.toLowerCase())
  );

  const toggle = (id: number) => {
    setRules((p) => p.map((r) => (r.id === id ? { ...r, is_active: !r.is_active } : r)));
  };

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search rules by name or description…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-md border border-input bg-muted/50 pl-9 pr-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>
        <div className="text-xs text-muted-foreground">
          <span className="font-mono text-foreground tabular">{rules.filter((r) => r.is_active).length}</span> active ·{" "}
          <span className="font-mono text-foreground tabular">{rules.length}</span> total
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition"
        >
          <Plus className="h-3.5 w-3.5" />
          New Rule
        </button>
      </div>

      {/* Rules grid */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {filtered.map((r) => (
          <RuleCard key={r.id} rule={r} onToggle={() => toggle(r.id)} />
        ))}
      </div>

      {showCreate && <CreateRuleModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function RuleCard({ rule, onToggle }: { rule: BusinessRule; onToggle: () => void }) {
  return (
    <Card
      className={cn(
        "p-4 transition-all hover:border-primary/30",
        !rule.is_active && "opacity-60"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="rounded-md bg-primary/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-primary">
              {TYPE_LABELS[rule.rule_type]}
            </span>
            <RiskBadge level={rule.risk_level_bump} size="sm" showDot={false} />
            <span className="text-[10px] text-muted-foreground">
              Priority <span className="font-mono tabular">{rule.priority}</span>
            </span>
          </div>
          <h3 className="text-sm font-semibold leading-snug">{rule.name}</h3>
          <p className="mt-1 text-[11px] text-muted-foreground line-clamp-2">{rule.description}</p>
        </div>
        <button
          onClick={onToggle}
          className={cn(
            "flex h-7 w-12 shrink-0 items-center rounded-full border px-0.5 transition-colors",
            rule.is_active
              ? "border-emerald-500/40 bg-emerald-500/15 justify-end"
              : "border-border bg-muted justify-start"
          )}
          title={rule.is_active ? "Disable" : "Enable"}
        >
          <span
            className={cn(
              "h-5 w-5 rounded-full transition-colors",
              rule.is_active ? "bg-emerald-400" : "bg-muted-foreground"
            )}
          />
        </button>
      </div>

      {/* Condition expression */}
      <div className="mt-3 rounded-md border border-border/60 bg-muted/40 p-2.5">
        <div className="mb-1 flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">
          <Settings2 className="h-2.5 w-2.5" />
          Condition (simpleeval)
        </div>
        <code className="font-mono text-[11px] text-[color:var(--signal)]">{rule.condition}</code>
      </div>

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-3 text-[10px] text-muted-foreground">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Zap className="h-2.5 w-2.5 text-amber-400" />
            Triggered <span className="font-mono tabular text-foreground">{formatNumber(rule.triggered_count)}</span>×
          </span>
          <span className="flex items-center gap-1">
            <Power className="h-2.5 w-2.5" />
            Action: <span className="font-medium text-foreground">{rule.action}</span>
          </span>
        </div>
        <span>{formatTimeAgo(rule.created_at)}</span>
      </div>
    </Card>
  );
}

function CreateRuleModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<BusinessRule["rule_type"]>("PATTERN");
  const [condition, setCondition] = useState("amount > 100000");
  const [action, setAction] = useState<BusinessRule["action"]>("flag");
  const [bump, setBump] = useState<BusinessRule["risk_level_bump"]>("MEDIUM");
  const [priority, setPriority] = useState(70);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <Card className="w-full max-w-2xl mx-4 p-0 overflow-hidden">
        <div className="flex items-center justify-between border-b border-border p-4">
          <h3 className="text-sm font-semibold">Create New Business Rule</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="scroll-thin max-h-[70vh] overflow-y-auto p-4 space-y-4">
          <div>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Impossible Travel Pattern"
              className="w-full rounded-md border border-input bg-muted/50 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Explain what this rule detects and why it matters."
              rows={2}
              className="w-full rounded-md border border-input bg-muted/50 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as BusinessRule["rule_type"])}
                className="w-full rounded-md border border-input bg-muted/50 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                {Object.entries(TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Action</label>
              <select
                value={action}
                onChange={(e) => setAction(e.target.value as BusinessRule["action"])}
                className="w-full rounded-md border border-input bg-muted/50 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="flag">Flag</option>
                <option value="escalate">Escalate</option>
                <option value="block">Block</option>
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Bump to</label>
              <select
                value={bump}
                onChange={(e) => setBump(e.target.value as BusinessRule["risk_level_bump"])}
                className="w-full rounded-md border border-input bg-muted/50 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Condition Expression
            </label>
            <p className="mb-1.5 text-[10px] text-muted-foreground">
              simpleeval syntax. Available vars: amount, type_encoded, type_risk_score, log_amount, balance_error_orig, sender_account_emptied, suspicious_signal_count, transactions_in_step, is_large_transaction, …
            </p>
            <textarea
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              rows={2}
              className="w-full rounded-md border border-input bg-muted/50 px-3 py-2 font-mono text-xs text-[color:var(--signal)] focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
            />
          </div>

          <div>
            <label className="mb-1.5 flex items-center justify-between text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              <span>Priority</span>
              <span className="font-mono tabular text-foreground">{priority}</span>
            </label>
            <input
              type="range"
              min={1}
              max={100}
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value))}
              className="w-full accent-primary"
            />
            <div className="flex justify-between text-[9px] text-muted-foreground/60">
              <span>Low (1)</span>
              <span>Critical (100)</span>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-border p-4">
          <button
            onClick={onClose}
            className="rounded-md border border-border px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition"
          >
            Cancel
          </button>
          <button
            onClick={onClose}
            className="rounded-md bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition"
          >
            Save Rule
          </button>
        </div>
      </Card>
    </div>
  );
}
