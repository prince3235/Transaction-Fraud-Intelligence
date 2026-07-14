"use client";

import { Card } from "@/components/ui/card";
import type { ShapContributor } from "@/lib/fraud-data";
import { cn } from "@/lib/utils";

interface ShapWaterfallProps {
  contributors: ShapContributor[];
}

export function ShapWaterfall({ contributors }: ShapWaterfallProps) {
  const maxAbs = Math.max(...contributors.map((c) => Math.abs(c.contribution)), 0.0001);
  const sorted = [...contributors].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));

  return (
    <Card className="p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold">SHAP Feature Contributions</h3>
        <p className="text-xs text-muted-foreground">
          TreeExplainer · top {sorted.length} features driving fraud probability
        </p>
      </div>

      <div className="space-y-2">
        {sorted.map((c) => {
          const widthPct = (Math.abs(c.contribution) / maxAbs) * 100;
          const isPositive = c.direction === "positive";
          return (
            <div key={c.feature} className="group">
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-mono text-muted-foreground group-hover:text-foreground transition">
                  {c.feature}
                </span>
                <span className="font-mono tabular">
                  <span className="text-muted-foreground">val={c.value.toFixed(2)}</span>
                  <span className={cn("ml-2 font-semibold", isPositive ? "text-red-400" : "text-emerald-400")}>
                    {isPositive ? "+" : "−"}{Math.abs(c.contribution).toFixed(4)}
                  </span>
                </span>
              </div>
              <div className="relative h-5 rounded-sm bg-muted/40 overflow-hidden">
                <div
                  className={cn(
                    "absolute inset-y-0 left-0 rounded-sm transition-all duration-700",
                    isPositive
                      ? "bg-gradient-to-r from-red-500/60 to-red-400"
                      : "bg-gradient-to-r from-emerald-500/60 to-emerald-400"
                  )}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 border-t border-border/60 pt-3 flex items-center justify-between text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-sm bg-red-400" /> Pushes risk ↑
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-3 rounded-sm bg-emerald-400" /> Pushes risk ↓
        </span>
        <span>Sum of contributions = P(fraud) − baseline</span>
      </div>
    </Card>
  );
}
