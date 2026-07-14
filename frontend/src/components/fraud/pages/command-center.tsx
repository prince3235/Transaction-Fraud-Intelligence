"use client";

import { MetricCard } from "@/components/fraud/metric-card";
import { RiskBadge } from "@/components/fraud/risk-badge";
import { Card } from "@/components/ui/card";
import { Activity, ShieldX, ShieldCheck, Gauge, TrendingUp, AlertTriangle, DollarSign, FolderKanban } from "lucide-react";
import { ALERTS, CASES, getStats, getAlertTrend } from "@/lib/fraud-data";
import {
  formatCompactCurrency,
  formatNumber,
  formatPercent,
  formatTimeAgo,
  RISK_COLORS,
} from "@/lib/fraud-utils";
import { cn } from "@/lib/utils";

const stats = getStats();
const trend = getAlertTrend();
const maxTrend = Math.max(...trend.map((t) => t.alerts));

const RISK_DIST = [
  { level: "CRITICAL" as const, count: stats.critical, color: "var(--risk-critical)" },
  { level: "HIGH" as const, count: stats.high, color: "var(--risk-high)" },
  { level: "MEDIUM" as const, count: stats.medium, color: "var(--risk-medium)" },
  { level: "LOW" as const, count: stats.low, color: "var(--risk-low)" },
];
const totalRisk = RISK_DIST.reduce((s, r) => s + r.count, 0);

export function CommandCenterPage() {
  const recentAlerts = ALERTS.slice()
    .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at))
    .slice(0, 6);

  return (
    <div className="space-y-6">
      {/* KPI Row 1 */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard
          label="Total Scored"
          value={formatNumber(stats.total)}
          icon={Activity}
          accent="signal"
          delta={{ value: 8.2, positive: true }}
          hint="vs last 24h"
        />
        <MetricCard
          label="Critical Alerts"
          value={stats.critical}
          icon={AlertTriangle}
          accent="critical"
          delta={{ value: 12.5, positive: false }}
          hint="vs yesterday"
        />
        <MetricCard
          label="Blocked"
          value={stats.blocked}
          icon={ShieldX}
          accent="high"
          delta={{ value: 4.1, positive: true }}
          hint="auto + manual"
        />
        <MetricCard
          label="Approved"
          value={stats.approved}
          icon={ShieldCheck}
          accent="low"
          delta={{ value: 2.3, positive: true }}
          hint="auto + manual"
        />
        <MetricCard
          label="Override Rate"
          value={formatPercent(stats.overrideRate)}
          icon={Gauge}
          accent="medium"
          hint="policy + rules"
        />
        <MetricCard
          label="Avg Risk Score"
          value={stats.avgScore}
          icon={TrendingUp}
          accent="default"
          hint="of all scored"
        />
      </div>

      {/* KPI Row 2 — Financial impact */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <MetricCard
          label="Total Volume Scanned"
          value={formatCompactCurrency(stats.totalAmount)}
          icon={DollarSign}
          accent="signal"
          className="lg:col-span-1"
        />
        <MetricCard
          label="Fraud Blocked (Saved)"
          value={formatCompactCurrency(stats.blockedAmount)}
          icon={ShieldCheck}
          accent="low"
          hint="blocked transactions"
        />
        <MetricCard
          label="Potential Loss (Approved HIGH+)"
          value={formatCompactCurrency(stats.potentialLoss)}
          icon={AlertTriangle}
          accent="critical"
          hint="needs review"
        />
      </div>

      {/* Trend + Risk distribution */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Alert trend — bar chart */}
        <Card className="p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Alert Trend</h3>
              <p className="text-xs text-muted-foreground">Last 14 days · alerts vs blocked</p>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="h-2 w-2 rounded-sm bg-[color:var(--signal)]/60" />
                Total alerts
              </span>
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="h-2 w-2 rounded-sm bg-[color:var(--risk-critical)]" />
                Blocked
              </span>
            </div>
          </div>
          <div className="flex h-44 items-end gap-1.5">
            {trend.map((d, i) => {
              const h = (d.alerts / maxTrend) * 100;
              const hb = (d.blocked / maxTrend) * 100;
              return (
                <div key={i} className="group relative flex flex-1 flex-col items-center gap-1">
                  <div className="relative flex h-full w-full items-end justify-center gap-0.5">
                    <div
                      className="w-1/2 rounded-t-sm bg-[color:var(--signal)]/40 transition-all group-hover:bg-[color:var(--signal)]/70"
                      style={{ height: `${h}%` }}
                    />
                    <div
                      className="w-1/2 rounded-t-sm bg-[color:var(--risk-critical)]/70 transition-all group-hover:bg-[color:var(--risk-critical)]"
                      style={{ height: `${hb}%` }}
                    />
                    {/* Tooltip */}
                    <div className="pointer-events-none absolute -top-14 left-1/2 -translate-x-1/2 rounded-md border border-border bg-popover px-2 py-1 text-[10px] opacity-0 transition-opacity group-hover:opacity-100">
                      <div className="font-mono tabular text-foreground">{d.alerts} alerts</div>
                      <div className="font-mono tabular text-red-400">{d.blocked} blocked</div>
                      <div className="text-muted-foreground">{d.date.slice(5)}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-2 flex justify-between text-[9px] font-mono tabular text-muted-foreground/60">
            {trend.filter((_, i) => i % 2 === 0).map((d) => (
              <span key={d.date}>{d.date.slice(5)}</span>
            ))}
          </div>
        </Card>

        {/* Risk distribution — donut */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Risk Distribution</h3>
          <p className="mb-4 text-xs text-muted-foreground">By final risk level</p>
          <div className="flex items-center justify-center">
            <div className="relative h-36 w-36">
              <DonutChart data={RISK_DIST} total={totalRisk} />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="font-mono text-2xl font-bold tabular">{totalRisk}</div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">total</div>
              </div>
            </div>
          </div>
          <div className="mt-4 space-y-1.5">
            {RISK_DIST.map((r) => (
              <div key={r.level} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-sm" style={{ background: r.color }} />
                  <span className="text-muted-foreground">{r.level}</span>
                </span>
                <span className="font-mono tabular">
                  {r.count} · {formatPercent((r.count / totalRisk) * 100, 0)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Recent alerts + open cases */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Recent alerts */}
        <Card className="p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Recent High-Risk Activity</h3>
              <p className="text-xs text-muted-foreground">Latest flagged transactions</p>
            </div>
            <button className="text-xs text-primary hover:underline">View all →</button>
          </div>
          <div className="space-y-1">
            {recentAlerts.map((a) => {
              const c = RISK_COLORS[a.final_risk_level];
              return (
                <div
                  key={a.id}
                  className="group flex items-center gap-3 rounded-md px-2 py-2 hover:bg-muted/50 transition cursor-pointer"
                >
                  <div className={cn("flex h-8 w-8 items-center justify-center rounded-md", c.bg)}>
                    <Activity className={cn("h-3.5 w-3.5", c.text)} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-medium">
                        {a.transaction.type} · {formatCompactCurrency(a.transaction.amount)}
                      </span>
                      <RiskBadge level={a.final_risk_level} size="sm" />
                    </div>
                    <div className="truncate text-[10px] text-muted-foreground">
                      {a.transaction.nameOrig} → {a.transaction.nameDest} · score {a.final_risk_score}
                    </div>
                  </div>
                  <span className="text-[10px] text-muted-foreground tabular">
                    {formatTimeAgo(a.created_at)}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Open cases */}
        <Card className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Open Cases</h3>
              <p className="text-xs text-muted-foreground">{stats.openCases} awaiting action</p>
            </div>
            <FolderKanban className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="space-y-2">
            {CASES.filter((c) => c.status === "OPEN" || c.status === "INVESTIGATING").slice(0, 5).map((c) => (
              <div
                key={c.id}
                className="rounded-md border border-border/60 p-2.5 hover:border-primary/40 transition cursor-pointer"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground">{c.case_id}</span>
                  <RiskBadge level={c.risk_level} size="sm" />
                </div>
                <p className="mt-1 line-clamp-2 text-xs leading-snug">{c.title}</p>
                <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground">
                  <span>{formatCompactCurrency(c.amount)}</span>
                  <span>{formatTimeAgo(c.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function DonutChart({ data, total }: { data: { level: string; count: number; color: string }[]; total: number }) {
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  // Use reduce to compute segments with cumulative offsets without mutating during render
  const segments = data.reduce<
    { key: string; color: string; len: number; offset: number }[]
  >((acc, d) => {
    const len = (d.count / total) * circumference;
    const prevOffset = acc.length > 0 ? acc[acc.length - 1].offset + acc[acc.length - 1].len : 0;
    acc.push({ key: d.level, color: d.color, len, offset: prevOffset });
    return acc;
  }, []);
  return (
    <svg width="144" height="144" viewBox="0 0 144 144" className="-rotate-90">
      <circle cx="72" cy="72" r={radius} fill="none" stroke="var(--muted)" strokeWidth="14" />
      {segments.map((s) => (
        <circle
          key={s.key}
          cx="72"
          cy="72"
          r={radius}
          fill="none"
          stroke={s.color}
          strokeWidth="14"
          strokeDasharray={`${s.len} ${circumference - s.len}`}
          strokeDashoffset={-s.offset}
          strokeLinecap="butt"
        />
      ))}
    </svg>
  );
}
