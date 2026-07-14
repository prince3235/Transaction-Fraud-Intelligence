"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Shield, ShieldCheck, Activity, AlertTriangle, ArrowRight, Loader2 } from "lucide-react";

interface LoginPageProps {
  onLogin: (user: { name: string; role: string }) => void;
}

const ROLES = [
  { value: "Admin", label: "Admin", desc: "Full access" },
  { value: "Fraud_Analyst", label: "Fraud Analyst", desc: "Investigate & resolve" },
  { value: "Compliance_Officer", label: "Compliance", desc: "Audit & export" },
  { value: "Auditor", label: "Auditor", desc: "Read-only" },
];

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("a.patel");
  const [password, setPassword] = useState("•••••••••");
  const [role, setRole] = useState("Fraud_Analyst");
  const [loading, setLoading] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      onLogin({ name: username, role });
      setLoading(false);
    }, 800);
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background">
      {/* Background grid + glow */}
      <div className="absolute inset-0 bg-grid opacity-40" />
      <div className="absolute left-1/2 top-0 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-[color:var(--signal)]/10 blur-3xl" />
      <div className="absolute bottom-0 right-1/3 h-[400px] w-[600px] rounded-full bg-[color:var(--ml)]/10 blur-3xl" />

      <div className="relative z-10 grid w-full max-w-5xl grid-cols-1 overflow-hidden rounded-2xl border border-border bg-card/80 backdrop-blur-xl md:grid-cols-2">
        {/* Left: brand panel */}
        <div className="relative hidden flex-col justify-between p-10 md:flex">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="relative flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/60 shadow-lg shadow-primary/30">
                <Shield className="h-5 w-5 text-primary-foreground" />
                <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-card bg-emerald-400" />
              </div>
              <div>
                <div className="font-mono text-base font-bold tracking-tight">SENTINEL</div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Fraud Intelligence</div>
              </div>
            </div>

            <h1 className="mt-10 text-2xl font-bold leading-tight">
              Real-time transaction fraud intelligence for modern fintechs.
            </h1>
            <p className="mt-3 text-sm text-muted-foreground">
              ML-powered scoring, explainable AI, case management, and immutable audit trails — built for compliance teams at scale.
            </p>
          </div>

          <div className="space-y-3">
            <FeatureRow icon={Activity} title="Sub-100ms inference" desc="RandomForest + SHAP, served at the gateway" />
            <FeatureRow icon={ShieldCheck} title="Explainable decisions" desc="Every block comes with feature attributions" />
            <FeatureRow icon={AlertTriangle} title="Live alert feed" desc="WebSocket push for high-risk transactions" />
          </div>

          <div className="border-t border-border pt-4 text-[10px] text-muted-foreground">
            SOC 2 Type II · PCI-DSS · ISO 27001
          </div>
        </div>

        {/* Right: login form */}
        <div className="flex flex-col justify-center p-8 md:p-10">
          <div className="mx-auto w-full max-w-sm">
            <div className="mb-8">
              <h2 className="text-xl font-semibold">Sign in</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Use your Sentinel credentials to access the operations console.
              </p>
            </div>

            <form onSubmit={submit} className="space-y-4">
              <div>
                <label htmlFor="username" className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full rounded-md border border-input bg-muted/50 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition"
                  placeholder="a.patel"
                  required
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-md border border-input bg-muted/50 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition"
                  placeholder="••••••••"
                  required
                />
              </div>

              <div>
                <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Role (demo)
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {ROLES.map((r) => (
                    <button
                      key={r.value}
                      type="button"
                      onClick={() => setRole(r.value)}
                      className={cn(
                        "rounded-md border px-2 py-2 text-left text-[10px] transition",
                        role === r.value
                          ? "border-primary/40 bg-primary/10"
                          : "border-border bg-transparent hover:bg-muted/50"
                      )}
                    >
                      <div className={cn("font-semibold", role === r.value ? "text-primary" : "text-foreground")}>
                        {r.label}
                      </div>
                      <div className="text-muted-foreground">{r.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 rounded-md border border-border/60 bg-muted/30 p-3 text-[11px] text-muted-foreground">
              <div className="font-semibold text-foreground mb-1">Demo access</div>
              This is a sandboxed preview. Pick any role to explore the platform — credentials are pre-filled.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureRow({ icon: Icon, title, desc }: { icon: typeof Activity; title: string; desc: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div>
        <div className="text-xs font-semibold">{title}</div>
        <div className="text-[11px] text-muted-foreground">{desc}</div>
      </div>
    </div>
  );
}
