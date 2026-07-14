"use client";

import { cn } from "@/lib/utils";
import { RISK_COLORS, STATUS_COLORS } from "@/lib/fraud-utils";
import type { RiskLevel } from "@/lib/fraud-data";

interface RiskBadgeProps {
  level: RiskLevel;
  size?: "sm" | "md" | "lg";
  showDot?: boolean;
  className?: string;
}

export function RiskBadge({ level, size = "md", showDot = true, className }: RiskBadgeProps) {
  const c = RISK_COLORS[level];
  const sizeClasses = {
    sm: "text-[10px] px-2 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5",
    lg: "text-sm px-3 py-1.5 gap-2",
  };
  const dotSize = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-2.5 h-2.5",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border font-semibold uppercase tracking-wider",
        c.bg,
        c.text,
        c.border,
        sizeClasses[size],
        className
      )}
    >
      {showDot && (
        <span className={cn("rounded-full", c.dot, dotSize[size])} />
      )}
      {level}
    </span>
  );
}

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function StatusBadge({ status, size = "md", className }: StatusBadgeProps) {
  const c = STATUS_COLORS[status] ?? STATUS_COLORS.PENDING_REVIEW;
  const sizeClasses = {
    sm: "text-[10px] px-2 py-0.5",
    md: "text-xs px-2.5 py-1",
    lg: "text-sm px-3 py-1.5",
  };
  const label = status.replace(/_/g, " ");
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium capitalize",
        c.bg,
        c.text,
        sizeClasses[size],
        className
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full", c.dot)} />
      {label}
    </span>
  );
}
