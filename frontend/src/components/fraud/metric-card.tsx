"use client";

import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: { value: number; positive?: boolean };
  icon?: LucideIcon;
  hint?: string;
  accent?: "default" | "low" | "medium" | "high" | "critical" | "signal";
  className?: string;
}

const ACCENT_STYLES = {
  default: "text-foreground",
  low: "text-[color:var(--risk-low)]",
  medium: "text-[color:var(--risk-medium)]",
  high: "text-[color:var(--risk-high)]",
  critical: "text-[color:var(--risk-critical)]",
  signal: "text-[color:var(--signal)]",
};

export function MetricCard({
  label,
  value,
  delta,
  icon: Icon,
  hint,
  accent = "default",
  className,
}: MetricCardProps) {
  return (
    <Card
      className={cn(
        "relative overflow-hidden p-5 transition-all hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5",
        className
      )}
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent opacity-60" />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {Icon && (
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
                <Icon className={cn("h-3.5 w-3.5", ACCENT_STYLES[accent])} />
              </div>
            )}
            <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              {label}
            </p>
          </div>
          <p className={cn("mt-3 font-mono text-2xl font-semibold tabular tracking-tight", ACCENT_STYLES[accent])}>
            {value}
          </p>
          {(delta || hint) && (
            <div className="mt-1.5 flex items-center gap-2 text-xs">
              {delta && (
                <span
                  className={cn(
                    "inline-flex items-center gap-0.5 font-medium tabular",
                    delta.positive ? "text-emerald-400" : "text-red-400"
                  )}
                >
                  {delta.positive ? "↑" : "↓"} {Math.abs(delta.value)}%
                </span>
              )}
              {hint && <span className="text-muted-foreground">{hint}</span>}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
