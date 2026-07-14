/**
 * React Query hooks for the Fraud Intelligence API.
 *
 * Wraps the api-client functions with TanStack Query for caching,
 * background refetching, and loading/error states.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAlerts,
  getCases,
  getRules,
  getModels,
  getAuditLogs,
  getApiStats,
  getAlertTrendData,
  predict,
  updateLogStatus,
  toggleRule,
  promoteModel,
  reloadModel,
  copilotExplain,
} from "./api-client";

// ── Query keys ───────────────────────────────────────────────────────────────

export const queryKeys = {
  alerts: ["alerts"] as const,
  cases: ["cases"] as const,
  rules: ["rules"] as const,
  models: ["models"] as const,
  auditLogs: ["audit-logs"] as const,
  stats: ["stats"] as const,
  alertTrend: ["alert-trend"] as const,
  copilot: (logId: number) => ["copilot", logId] as const,
};

// ── Queries ──────────────────────────────────────────────────────────────────

export function useAlerts(limit = 50) {
  return useQuery({
    queryKey: [...queryKeys.alerts, limit],
    queryFn: () => getAlerts(limit),
    staleTime: 15_000, // 15 seconds
    refetchInterval: 30_000, // auto-refresh every 30s
  });
}

export function useCases() {
  return useQuery({
    queryKey: queryKeys.cases,
    queryFn: getCases,
    staleTime: 30_000,
  });
}

export function useRules() {
  return useQuery({
    queryKey: queryKeys.rules,
    queryFn: getRules,
    staleTime: 60_000,
  });
}

export function useModels() {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: getModels,
    staleTime: 60_000,
  });
}

export function useAuditLogs(limit = 50) {
  return useQuery({
    queryKey: [...queryKeys.auditLogs, limit],
    queryFn: () => getAuditLogs(limit),
    staleTime: 30_000,
  });
}

export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: getApiStats,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useAlertTrend() {
  return useQuery({
    queryKey: queryKeys.alertTrend,
    queryFn: getAlertTrendData,
    staleTime: 5 * 60_000, // 5 minutes
  });
}

// ── Mutations ────────────────────────────────────────────────────────────────

export function usePredict() {
  return useMutation({
    mutationFn: predict,
  });
}

export function useUpdateLogStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ logId, status }: { logId: number; status: "APPROVED" | "BLOCKED" }) =>
      updateLogStatus(logId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.alerts });
      qc.invalidateQueries({ queryKey: queryKeys.stats });
    },
  });
}

export function useToggleRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, isActive }: { ruleId: number; isActive: boolean }) =>
      toggleRule(ruleId, isActive),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.rules });
    },
  });
}

export function usePromoteModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: promoteModel,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.models });
    },
  });
}

export function useReloadModel() {
  return useMutation({
    mutationFn: reloadModel,
  });
}

export function useCopilot() {
  return useMutation({
    mutationFn: ({ logId, followUp }: { logId: number; followUp?: string }) =>
      copilotExplain(logId, followUp),
  });
}
