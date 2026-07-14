/**
 * Shared helpers for the fraud platform UI.
 */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { RiskLevel } from "./fraud-data";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format currency — Indian numbering system since the demo customers are INR-shaped. */
export function formatCurrency(amount: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Compact currency — $1.2M, $45K, $3.4K — for dashboard tiles. */
export function formatCompactCurrency(amount: number): string {
  if (Math.abs(amount) >= 1_000_000) return `$${(amount / 1_000_000).toFixed(2)}M`;
  if (Math.abs(amount) >= 1_000) return `$${(amount / 1_000).toFixed(1)}K`;
  return `$${amount.toFixed(0)}`;
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

export function formatPercent(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`;
}

export function formatProbability(p: number): string {
  return `${(p * 100).toFixed(2)}%`;
}

export function formatTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

/** Risk level → color tokens (used by badges, bars, charts). */
export const RISK_COLORS: Record<RiskLevel, {
  bg: string;
  text: string;
  border: string;
  dot: string;
  hex: string;
}> = {
  LOW: {
    bg: "bg-[color:var(--risk-low)]/15",
    text: "text-[color:var(--risk-low)]",
    border: "border-[color:var(--risk-low)]/30",
    dot: "bg-[color:var(--risk-low)]",
    hex: "#34d399",
  },
  MEDIUM: {
    bg: "bg-[color:var(--risk-medium)]/15",
    text: "text-[color:var(--risk-medium)]",
    border: "border-[color:var(--risk-medium)]/30",
    dot: "bg-[color:var(--risk-medium)]",
    hex: "#fbbf24",
  },
  HIGH: {
    bg: "bg-[color:var(--risk-high)]/15",
    text: "text-[color:var(--risk-high)]",
    border: "border-[color:var(--risk-high)]/30",
    dot: "bg-[color:var(--risk-high)]",
    hex: "#fb923c",
  },
  CRITICAL: {
    bg: "bg-[color:var(--risk-critical)]/15",
    text: "text-[color:var(--risk-critical)]",
    border: "border-[color:var(--risk-critical)]/30",
    dot: "bg-[color:var(--risk-critical)]",
    hex: "#f87171",
  },
};

export const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  PENDING_REVIEW: {
    bg: "bg-amber-500/15",
    text: "text-amber-400",
    dot: "bg-amber-400",
  },
  APPROVED: {
    bg: "bg-emerald-500/15",
    text: "text-emerald-400",
    dot: "bg-emerald-400",
  },
  BLOCKED: {
    bg: "bg-red-500/15",
    text: "text-red-400",
    dot: "bg-red-400",
  },
  ESCALATED: {
    bg: "bg-purple-500/15",
    text: "text-purple-400",
    dot: "bg-purple-400",
  },
  OPEN: {
    bg: "bg-amber-500/15",
    text: "text-amber-400",
    dot: "bg-amber-400",
  },
  INVESTIGATING: {
    bg: "bg-blue-500/15",
    text: "text-blue-400",
    dot: "bg-blue-400",
  },
  RESOLVED: {
    bg: "bg-emerald-500/15",
    text: "text-emerald-400",
    dot: "bg-emerald-400",
  },
};
