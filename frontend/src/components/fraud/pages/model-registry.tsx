"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { MODELS } from "@/lib/fraud-data";
import type { ModelVersion } from "@/lib/fraud-data";
import { formatDateTime, formatNumber } from "@/lib/fraud-utils";
import { Boxes, Rocket, Archive, CheckCircle2, GitBranch, Cpu, Database, Activity } from "lucide-react";

export function ModelRegistryPage() {
  const [models, setModels] = useState<ModelVersion[]>(MODELS);
  const [showArchived, setShowArchived] = useState(false);
  const [promoting, setPromoting] = useState<ModelVersion | null>(null);

  const visible = models.filter((m) => showArchived || !m.is_archived);
  const active = models.find((m) => m.is_production);

  const promote = (version: string) => {
    setModels((p) =>
      p.map((m) => ({
        ...m,
        is_production: m.version === version,
        is_archived: m.is_production ? false : m.is_archived,
      }))
    );
    setPromoting(null);
  };
  const archive = (version: string) => {
    setModels((p) => p.map((m) => (m.version === version ? { ...m, is_archived: true, is_production: false } : m)));
  };

  return (
    <div className="space-y-4">
      {/* Active model highlight */}
      {active && (
        <Card className="relative overflow-hidden p-5">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[color:var(--signal)] to-transparent" />
          <div className="absolute -right-12 -top-12 h-40 w-40 rounded-full bg-[color:var(--signal)]/5 blur-3xl" />

          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[color:var(--signal)]/15">
                <Boxes className="h-6 w-6 text-[color:var(--signal)]" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--signal)]">
                    Active Production Model
                  </span>
                  <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[9px] font-semibold text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    LIVE
                  </span>
                </div>
                <h2 className="mt-1 font-mono text-2xl font-bold tracking-tight">{active.version}</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Trained {formatDateTime(active.training_date)} · {formatNumber(active.dataset_size)} rows · {active.feature_count} features
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <Metric label="ROC AUC" value={active.roc_auc.toFixed(4)} color="emerald" />
              <Metric label="PR AUC" value={active.pr_auc.toFixed(4)} color="emerald" />
              <Metric label="F1" value={active.f1.toFixed(4)} color="signal" />
              <Metric label="Precision" value={active.precision.toFixed(4)} color="default" />
              <Metric label="Recall" value={active.recall.toFixed(4)} color="default" />
            </div>
          </div>

          <p className="mt-3 border-t border-border/60 pt-3 text-xs text-muted-foreground">
            {active.notes}
          </p>
        </Card>
      )}

      {/* Header + filter */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Version History</h3>
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="accent-primary"
          />
          Show archived
        </label>
      </div>

      {/* Versions table */}
      <Card className="overflow-hidden p-0">
        <table className="w-full text-xs">
          <thead className="bg-muted/40">
            <tr className="border-b border-border text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3 text-left">Version</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-right">ROC AUC</th>
              <th className="px-4 py-3 text-right">PR AUC</th>
              <th className="px-4 py-3 text-right">F1</th>
              <th className="px-4 py-3 text-right">Estimators</th>
              <th className="px-4 py-3 text-right">Dataset</th>
              <th className="px-4 py-3 text-left">Trained</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((m) => (
              <tr key={m.id} className="border-b border-border/40 hover:bg-muted/30 transition">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold">{m.version}</span>
                    {m.is_production && (
                      <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-400">
                        <CheckCircle2 className="h-2.5 w-2.5" />
                        PROD
                      </span>
                    )}
                    {m.is_archived && (
                      <span className="rounded-full bg-muted px-1.5 py-0.5 text-[9px] font-semibold text-muted-foreground">
                        ARCHIVED
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-muted-foreground">
                    {m.is_production ? "Production" : m.is_archived ? "Archived" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono tabular text-emerald-400">{m.roc_auc.toFixed(4)}</td>
                <td className="px-4 py-3 text-right font-mono tabular text-emerald-400">{m.pr_auc.toFixed(4)}</td>
                <td className="px-4 py-3 text-right font-mono tabular">{m.f1.toFixed(4)}</td>
                <td className="px-4 py-3 text-right font-mono tabular">{m.n_estimators}</td>
                <td className="px-4 py-3 text-right font-mono tabular">{formatNumber(m.dataset_size)}</td>
                <td className="px-4 py-3 text-[10px] text-muted-foreground">{formatDateTime(m.training_date)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {!m.is_production && !m.is_archived && (
                      <>
                        <button
                          onClick={() => setPromoting(m)}
                          className="flex items-center gap-1 rounded-md bg-[color:var(--signal)]/15 px-2 py-1 text-[10px] font-medium text-[color:var(--signal)] hover:bg-[color:var(--signal)]/25 transition"
                          title="Promote to production"
                        >
                          <Rocket className="h-3 w-3" />
                          Promote
                        </button>
                        <button
                          onClick={() => archive(m.version)}
                          className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] font-medium text-muted-foreground hover:text-foreground transition"
                          title="Archive"
                        >
                          <Archive className="h-3 w-3" />
                        </button>
                      </>
                    )}
                    {m.is_production && (
                      <span className="text-[10px] text-emerald-400">Currently serving</span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Training details */}
      <Card className="p-5">
        <h3 className="mb-3 text-sm font-semibold">Model Architecture</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <InfoTile icon={Cpu} label="Algorithm" value="RandomForest" hint="scikit-learn" />
          <InfoTile icon={GitBranch} label="Split Strategy" value="Temporal" hint="steps 1-600 train" />
          <InfoTile icon={Database} label="Imbalance" value="balanced_subsample" hint="class_weight" />
          <InfoTile icon={Activity} label="Calibration" value="Isotonic" hint="Platt fallback" />
        </div>
      </Card>

      {/* Promote confirmation modal */}
      {promoting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <Card className="mx-4 w-full max-w-md p-5">
            <div className="flex items-start gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-amber-500/15">
                <Rocket className="h-5 w-5 text-amber-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold">Promote {promoting.version} to production?</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  This will swap the active model served by the API. The current production model will become inactive.
                </p>
              </div>
            </div>

            <div className="rounded-md border border-border/60 p-3 mb-4 space-y-1.5 text-xs">
              <div className="flex justify-between"><span className="text-muted-foreground">ROC AUC</span><span className="font-mono tabular">{promoting.roc_auc.toFixed(4)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">PR AUC</span><span className="font-mono tabular">{promoting.pr_auc.toFixed(4)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">F1</span><span className="font-mono tabular">{promoting.f1.toFixed(4)}</span></div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setPromoting(null)}
                className="rounded-md border border-border px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition"
              >
                Cancel
              </button>
              <button
                onClick={() => promote(promoting.version)}
                className="rounded-md bg-[color:var(--signal)] px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 transition"
              >
                Confirm Promotion
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color: "emerald" | "signal" | "default" }) {
  const colors = {
    emerald: "text-emerald-400",
    signal: "text-[color:var(--signal)]",
    default: "text-foreground",
  };
  return (
    <div className="text-right">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("font-mono text-lg font-bold tabular", colors[color])}>{value}</div>
    </div>
  );
}

function InfoTile({ icon: Icon, label, value, hint }: { icon: typeof Cpu; label: string; value: string; hint: string }) {
  return (
    <div className="rounded-md border border-border/60 p-3">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <div className="font-mono text-sm font-semibold">{value}</div>
      <div className="text-[10px] text-muted-foreground">{hint}</div>
    </div>
  );
}
