"use client";

import { cn } from "@/lib/utils";

interface RiskBarProps {
  score: number;
  level?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  showScale?: boolean;
  className?: string;
}

export function RiskBar({ score, level, showScale = true, className }: RiskBarProps) {
  const safeScore = Math.max(0, Math.min(100, score));
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
        <div className="absolute inset-y-0 left-[40%] w-px bg-background/50" />
        <div className="absolute inset-y-0 left-[70%] w-px bg-background/50" />
        <div className="absolute inset-y-0 left-[85%] w-px bg-background/50" />
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${safeScore}%`,
            background:
              safeScore < 40
                ? "var(--risk-low)"
                : safeScore < 70
                ? "var(--risk-medium)"
                : safeScore < 85
                ? "var(--risk-high)"
                : "var(--risk-critical)",
          }}
        />
      </div>
      {showScale && (
        <div className="flex justify-between text-[9px] font-medium tabular text-muted-foreground/70">
          <span>LOW</span>
          <span className="ml-[36%]">MED</span>
          <span className="-ml-2">HIGH</span>
          <span>CRIT</span>
        </div>
      )}
    </div>
  );
}
