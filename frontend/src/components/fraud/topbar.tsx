"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { Search, Bell, Activity, Wifi, AlertTriangle } from "lucide-react";
import { RECENT_TICKER_ALERTS } from "@/lib/fraud-data";
import { formatCompactCurrency, formatTimeAgo, RISK_COLORS } from "@/lib/fraud-utils";
import { RiskBadge } from "./risk-badge";

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  "command-center": { title: "Command Center", subtitle: "Real-time fraud intelligence overview" },
  alerts: { title: "Alerts Monitoring", subtitle: "Investigate and adjudicate flagged transactions" },
  cases: { title: "Case Management", subtitle: "Track and resolve fraud investigations" },
  simulation: { title: "Simulation Lab", subtitle: "Test the ML model with synthetic transactions" },
  rules: { title: "Rules Engine", subtitle: "Configure heuristic fraud detection rules" },
  "model-registry": { title: "Model Registry", subtitle: "Track, promote, and roll back ML model versions" },
  audit: { title: "Audit Logs", subtitle: "Immutable record of all platform actions" },
};

interface TopbarProps {
  page: string;
}

export function Topbar({ page }: TopbarProps) {
  const [now, setNow] = useState(new Date());
  const [wsConnected, setWsConnected] = useState(true);
  const [notifOpen, setNotifOpen] = useState(false);
  const meta = PAGE_TITLES[page] ?? PAGE_TITLES["command-center"];

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // Simulate occasional WS drops for visual richness
  useEffect(() => {
    const t = setInterval(() => {
      setWsConnected((p) => (Math.random() > 0.05 ? true : !p));
    }, 8000);
    return () => clearInterval(t);
  }, []);

  const criticalCount = RECENT_TICKER_ALERTS.filter(
    (a) => a.final_risk_level === "CRITICAL" || a.final_risk_level === "HIGH"
  ).length;

  return (
    <header className="sticky top-0 z-30 flex h-16 flex-col border-b border-border bg-background/80 backdrop-blur-xl">
      {/* Row 1: title + actions */}
      <div className="flex h-16 items-center gap-4 px-6">
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base font-semibold tracking-tight">{meta.title}</h1>
          <p className="truncate text-xs text-muted-foreground">{meta.subtitle}</p>
        </div>

        {/* Search */}
        <div className="relative hidden lg:block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by case ID, customer, or amount…"
            className="h-9 w-72 rounded-md border border-input bg-muted/50 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition"
          />
          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-border bg-background px-1.5 py-0.5 text-[9px] font-mono text-muted-foreground">⌘K</kbd>
        </div>

        {/* WS status */}
        <div
          className={cn(
            "hidden md:flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium",
            wsConnected
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : "border-amber-500/30 bg-amber-500/10 text-amber-400"
          )}
        >
          {wsConnected ? (
            <>
              <Activity className="h-3 w-3" />
              <span>LIVE</span>
              <span className="relative ml-0.5 flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
              </span>
            </>
          ) : (
            <>
              <Wifi className="h-3 w-3" />
              <span>RECONNECTING</span>
            </>
          )}
        </div>

        {/* Clock */}
        <div className="hidden xl:block font-mono text-xs tabular text-muted-foreground">
          {now.toLocaleTimeString("en-US", { hour12: false })}
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setNotifOpen((p) => !p)}
            className="relative flex h-9 w-9 items-center justify-center rounded-md border border-input bg-muted/50 text-muted-foreground hover:text-foreground hover:border-primary/40 transition"
          >
            <Bell className="h-4 w-4" />
            {criticalCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">
                {criticalCount}
              </span>
            )}
          </button>
          {notifOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setNotifOpen(false)} />
              <div className="absolute right-0 top-11 z-50 w-80 rounded-lg border border-border bg-popover p-1.5 shadow-xl">
                <div className="px-3 py-2 text-xs font-semibold text-foreground">High-risk alerts</div>
                <div className="scroll-thin max-h-80 overflow-y-auto">
                  {RECENT_TICKER_ALERTS.slice(0, 6).map((a) => {
                    const c = RISK_COLORS[a.final_risk_level];
                    return (
                      <div
                        key={a.id}
                        className="flex items-center gap-3 rounded-md px-3 py-2 hover:bg-muted/50 transition cursor-pointer"
                      >
                        <div className={cn("h-1.5 w-1.5 rounded-full", c.dot)} />
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-xs font-medium">
                            {a.transaction.type} · {formatCompactCurrency(a.transaction.amount)}
                          </div>
                          <div className="truncate text-[10px] text-muted-foreground">
                            {a.transaction.nameOrig} → {a.transaction.nameDest}
                          </div>
                        </div>
                        <span className="text-[10px] text-muted-foreground tabular">
                          {formatTimeAgo(a.created_at)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Row 2: live alert ticker */}
      <div className="flex h-8 items-center gap-2 border-t border-border/60 bg-sidebar/50 px-6 overflow-hidden">
        <div className="flex shrink-0 items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-red-400">
          <AlertTriangle className="h-3 w-3" />
          Live Feed
        </div>
        <div className="relative flex-1 overflow-hidden">
          <div className="marquee flex gap-6 whitespace-nowrap text-xs">
            {[...RECENT_TICKER_ALERTS, ...RECENT_TICKER_ALERTS].map((a, i) => {
              const c = RISK_COLORS[a.final_risk_level];
              return (
                <span key={i} className="inline-flex items-center gap-2">
                  <span className={cn("h-1.5 w-1.5 rounded-full", c.dot)} />
                  <span className="font-mono text-muted-foreground">{a.transaction.nameOrig}</span>
                  <span className="text-muted-foreground/60">→</span>
                  <span className="font-mono text-muted-foreground">{a.transaction.nameDest}</span>
                  <span className="font-mono tabular text-foreground/80">
                    {formatCompactCurrency(a.transaction.amount)}
                  </span>
                  <RiskBadge level={a.final_risk_level} size="sm" showDot={false} />
                  <span className="text-muted-foreground/60">·</span>
                </span>
              );
            })}
          </div>
        </div>
      </div>
    </header>
  );
}
