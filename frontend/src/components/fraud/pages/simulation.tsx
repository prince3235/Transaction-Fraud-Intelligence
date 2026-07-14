"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { RiskBadge } from "@/components/fraud/risk-badge";
import { RiskBar } from "@/components/fraud/risk-bar";
import { cn } from "@/lib/utils";
import { formatCompactCurrency, formatProbability } from "@/lib/fraud-utils";
import { usePredict } from "@/lib/api-hooks";
import { FlaskConical, Play, RotateCcw, Activity, Cpu, Zap } from "lucide-react";

const TX_TYPES = [
  { value: "CASH_IN", label: "Cash In", risk: 1 },
  { value: "CASH_OUT", label: "Cash Out", risk: 3 },
  { value: "DEBIT", label: "Debit", risk: 2 },
  { value: "PAYMENT", label: "Payment", risk: 1 },
  { value: "TRANSFER", label: "Transfer", risk: 3 },
] as const;

interface SimResult {
  probability: number;
  riskScore: number;
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  reasons: string[];
  features: { name: string; value: string; impact: "high" | "medium" | "low" }[];
}

export function SimulationPage() {
  const [type, setType] = useState<(typeof TX_TYPES)[number]["value"]>("TRANSFER");
  const [amount, setAmount] = useState(150000);
  const [oldBalOrig, setOldBalOrig] = useState(200000);
  const [newBalOrig, setNewBalOrig] = useState(0);
  const [oldBalDest, setOldBalDest] = useState(0);
  const [newBalDest, setNewBalDest] = useState(150000);
  const [step, setStep] = useState(420);
  const [result, setResult] = useState<SimResult | null>(null);
  const [loading, setLoading] = useState(false);
  const predictMutation = usePredict();

  const run = async () => {
    setLoading(true);
    try {
      // Call the real API (falls back to mock prediction if backend unreachable)
      const apiResult = await predictMutation.mutateAsync({
        step,
        type,
        amount,
        oldbalanceOrg: oldBalOrig,
        newbalanceOrig: newBalOrig,
        oldbalanceDest: oldBalDest,
        newbalanceDest: newBalDest,
      });

      // Compute display features locally (the API returns risk, not features)
      const ratio = amount / Math.max(1, oldBalOrig);
      const emptied = oldBalOrig > 0 && newBalOrig === 0 ? 1 : 0;
      const destLarge = oldBalDest === 0 && newBalDest > 10000 ? 1 : 0;
      const balanceErr = Math.abs(newBalOrig - (oldBalOrig - amount));

      setResult({
        probability: apiResult.ml_probability,
        riskScore: apiResult.final_risk_score,
        riskLevel: apiResult.final_risk_level as SimResult["riskLevel"],
        reasons: apiResult.policy_reasons,
        features: [
          { name: "amount_to_oldbalance_orig_ratio", value: ratio.toFixed(3), impact: "high" },
          { name: "sender_account_emptied", value: emptied.toString(), impact: "high" },
          { name: "dest_received_large_amount", value: destLarge.toString(), impact: "medium" },
          { name: "balance_error_orig", value: balanceErr.toFixed(2), impact: "medium" },
          { name: "log_amount", value: Math.log1p(amount).toFixed(2), impact: "low" },
          { name: "type_risk_score", value: (TX_TYPES.find((t) => t.value === type)?.risk ?? 0).toString(), impact: "low" },
        ],
      });
    } catch (err) {
      // Fallback: compute locally (shouldn't happen — api-client has its own fallback)
      console.error("Prediction failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setType("TRANSFER");
    setAmount(150000);
    setOldBalOrig(200000);
    setNewBalOrig(0);
    setOldBalDest(0);
    setNewBalDest(150000);
    setStep(420);
    setResult(null);
  };

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      {/* Left: input form */}
      <Card className="p-5">
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[color:var(--signal)]/15">
            <FlaskConical className="h-4 w-4 text-[color:var(--signal)]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Transaction Sandbox</h3>
            <p className="text-xs text-muted-foreground">Submit a synthetic transaction to score against the ML model + rules</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* Type */}
          <div>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Transaction Type</label>
            <div className="grid grid-cols-5 gap-1">
              {TX_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setType(t.value)}
                  className={cn(
                    "rounded-md border px-2 py-2 text-[10px] font-medium transition",
                    type === t.value
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : "border-border bg-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Amount */}
          <NumberField label="Amount (USD)" value={amount} onChange={setAmount} prefix="$" />
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Sender Old Balance" value={oldBalOrig} onChange={setOldBalOrig} prefix="$" />
            <NumberField label="Sender New Balance" value={newBalOrig} onChange={setNewBalOrig} prefix="$" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Recipient Old Balance" value={oldBalDest} onChange={setOldBalDest} prefix="$" />
            <NumberField label="Recipient New Balance" value={newBalDest} onChange={setNewBalDest} prefix="$" />
          </div>
          <NumberField label="Step (1-743)" value={step} onChange={setStep} />

          <div className="flex gap-2 pt-2">
            <button
              onClick={run}
              disabled={loading}
              className="flex flex-1 items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition"
            >
              <Play className="h-4 w-4" />
              {loading ? "Scoring…" : "Score Transaction"}
            </button>
            <button
              onClick={reset}
              className="flex items-center justify-center gap-2 rounded-md border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground transition"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </button>
          </div>
        </div>
      </Card>

      {/* Right: result */}
      <div>
        {result ? (
          <Card className="p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-semibold">Prediction Result</h3>
                <p className="text-xs text-muted-foreground">ML inference + policy + rules engine</p>
              </div>
              <RiskBadge level={result.riskLevel} size="lg" />
            </div>

            {/* Score panel */}
            <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Cpu className="h-3.5 w-3.5 text-[color:var(--signal)]" />
                  ML Probability
                </div>
                <span className="font-mono text-2xl font-bold tabular text-[color:var(--signal)]">
                  {formatProbability(result.probability)}
                </span>
              </div>
              <div className="mt-3">
                <RiskBar score={result.riskScore} />
              </div>
              <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                <span>Risk Score</span>
                <span className="font-mono tabular font-semibold text-foreground">{result.riskScore}/100</span>
              </div>
            </div>

            {/* Reasons */}
            {result.reasons.length > 0 && (
              <div>
                <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Triggered Policies & Rules ({result.reasons.length})
                </h4>
                <div className="space-y-1.5">
                  {result.reasons.map((r, i) => (
                    <div key={i} className="flex items-start gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 p-2.5 text-xs">
                      <Zap className="mt-0.5 h-3 w-3 shrink-0 text-amber-400" />
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Engineered features */}
            <div>
              <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Engineered Features
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {result.features.map((f) => (
                  <div key={f.name} className="rounded-md border border-border/60 p-2.5">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="font-mono text-[10px] text-muted-foreground truncate">{f.name}</span>
                      <span
                        className={cn(
                          "rounded px-1 py-0.5 text-[8px] font-bold uppercase",
                          f.impact === "high" ? "bg-red-500/15 text-red-400" :
                          f.impact === "medium" ? "bg-amber-500/15 text-amber-400" :
                          "bg-muted text-muted-foreground"
                        )}
                      >
                        {f.impact}
                      </span>
                    </div>
                    <div className="font-mono text-sm tabular font-semibold">{f.value}</div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        ) : (
          <Card className="flex h-full min-h-[400px] flex-col items-center justify-center p-8 text-center">
            <Activity className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-sm font-medium text-muted-foreground">Ready to score</p>
            <p className="mt-1 max-w-xs text-xs text-muted-foreground/70">
              Configure a transaction on the left and click <strong>Score Transaction</strong> to run it through the ML model and rules engine.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  prefix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  prefix?: string;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </label>
      <div className="relative">
        {prefix && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-xs text-muted-foreground">
            {prefix}
          </span>
        )}
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
          className={cn(
            "w-full rounded-md border border-input bg-muted/50 py-2 pr-3 text-sm font-mono tabular focus:outline-none focus:ring-2 focus:ring-primary/40",
            prefix ? "pl-7" : "pl-3"
          )}
        />
      </div>
    </div>
  );
}
