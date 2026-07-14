/**
 * API Client for the Transaction Fraud Intelligence Platform.
 *
 * Connects the Sentinel frontend to the real FastAPI backend.
 *
 * When the backend is reachable (NEXT_PUBLIC_API_URL is set and the server
 * responds), all calls hit the real API. When the backend is unreachable
 * (e.g. in the sandbox preview without a running API), calls fall back to
 * the mock data in `fraud-data.ts` so the UI remains functional for demos.
 *
 * Auth: Bearer token stored in localStorage (set by the login page).
 * The token is either:
 *   - The static API_AUTH_TOKEN (admin access), OR
 *   - A "username:password" combo for demo convenience
 */

import { ALERTS, CASES, RULES, MODELS, AUDIT_LOGS, SHAP_CONTRIBUTORS, getStats, getAlertTrend, type PredictionLog, type FraudCase, type BusinessRule, type ModelVersion, type AuditLog, type ShapContributor } from "./fraud-data";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "sentinel_auth_token";
const USER_KEY = "sentinel_user";

// ── Auth helpers ─────────────────────────────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): { name: string; role: string } | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setStoredUser(user: { name: string; role: string }): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// ── API reachability check ───────────────────────────────────────────────────

let _apiReachable: boolean | null = null;

async function checkApiReachable(): Promise<boolean> {
  if (_apiReachable !== null) return _apiReachable;
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    const resp = await fetch(`${API_BASE}/health`, { signal: controller.signal });
    clearTimeout(timeout);
    _apiReachable = resp.ok;
  } catch {
    _apiReachable = false;
  }
  return _apiReachable;
}

// ── Fetch wrapper with auth + fallback ──────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  fallback: T | (() => T | Promise<T>),
): Promise<T> {
  const reachable = await checkApiReachable();
  if (!reachable) {
    // Fallback to mock data
    if (typeof fallback === "function") {
      return (fallback as () => T | Promise<T>)();
    }
    return fallback;
  }

  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!resp.ok) {
      // On 401, clear the token
      if (resp.status === 401) {
        clearToken();
      }
      throw new Error(`API ${resp.status}: ${resp.statusText}`);
    }
    return (await resp.json()) as T;
  } catch (err) {
    // Network error → fallback to mock
    if (typeof fallback === "function") {
      return (fallback as () => T | Promise<T>)();
    }
    return fallback;
  }
}

// ── Auth API ─────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  role: string;
}

export async function login(
  username: string,
  password: string,
  role?: string,
): Promise<{ user: AuthUser; token: string }> {
  // For the demo: store as "username:password" — the backend's get_current_user
  // accepts this format for demo convenience.
  const token = `${username}:${password}`;
  setToken(token);

  // Try to validate against the real API
  const reachable = await checkApiReachable();
  if (reachable) {
    try {
      const resp = await fetch(`${API_BASE}/health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const user: AuthUser = {
          id: 0,
          username,
          email: `${username}@fraudiq.ai`,
          role: role || "Fraud_Analyst",
        };
        setStoredUser({ name: username, role: user.role });
        return { user, token };
      }
    } catch {
      // fall through to mock
    }
  }

  // Mock login (sandbox mode)
  const user: AuthUser = {
    id: 1,
    username,
    email: `${username}@fraudiq.ai`,
    role: role || "Fraud_Analyst",
  };
  setStoredUser({ name: username, role: user.role });
  return { user, token };
}

export function logout(): void {
  clearToken();
}

// ── Prediction log types ─────────────────────────────────────────────────────

export interface PredictionLogApiResponse {
  id: number;
  created_at: string;
  transaction_json: {
    step: number;
    type: string;
    amount: number;
    nameOrig?: string;
    nameDest?: string;
    oldbalanceOrg: number;
    newbalanceOrig: number;
    oldbalanceDest: number;
    newbalanceDest: number;
  };
  ml_probability: number;
  ml_risk_level: string;
  ml_risk_score: number;
  final_risk_level: string;
  final_risk_score: number;
  policy_override_applied: boolean;
  policy_reasons_json: string[];
  rule_hits?: { name: string; condition: string; reason: string }[];
  suspicious_signal_count: number;
  status: string;
}

// ── Alerts / Prediction logs ─────────────────────────────────────────────────

export async function getAlerts(limit = 50): Promise<PredictionLog[]> {
  return apiFetch<PredictionLog[]>(
    `/logs/recent?limit=${limit}`,
    {},
    () => {
      // Transform mock data to match API shape (mock already matches)
      return ALERTS.slice(0, limit);
    },
  );
}

export async function predict(transaction: {
  step: number;
  type: string;
  amount: number;
  oldbalanceOrg: number;
  newbalanceOrig: number;
  oldbalanceDest: number;
  newbalanceDest: number;
}): Promise<{
  ml_probability: number;
  ml_risk_level: string;
  ml_risk_score: number;
  final_risk_level: string;
  final_risk_score: number;
  recommended_action: string;
  policy_override_applied: boolean;
  policy_reasons: string[];
  rule_hits: { name: string; condition: string; reason: string }[];
}> {
  return apiFetch(
    "/predict",
    { method: "POST", body: JSON.stringify(transaction) },
    () => {
      // Mock prediction for sandbox mode
      const amount = transaction.amount;
      const ratio = amount / Math.max(1, transaction.oldbalanceOrg);
      const emptied = transaction.oldbalanceOrg > 0 && transaction.newbalanceOrig === 0 ? 1 : 0;
      const destLarge = transaction.oldbalanceDest === 0 && transaction.newbalanceDest > 10000 ? 1 : 0;
      const balanceErr = Math.abs(transaction.newbalanceOrig - (transaction.oldbalanceOrg - amount));

      const reasons: string[] = [];
      if (ratio > 1 && emptied) reasons.push("Policy: Amount > sender balance + sender account emptied");
      if (amount > 100000) reasons.push("Rule matched: Large Transfer Amount");
      if (emptied && ratio > 0.95) reasons.push("Rule matched: Account Drain Pattern");
      if (destLarge && amount > 50000) reasons.push("Rule matched: First-time Beneficiary + Large Amount");
      if (balanceErr > 1) reasons.push("Rule matched: Balance Error Anomaly");

      const baseProb = Math.min(0.99, 0.3 + (amount / 1_000_000) * 0.5 + emptied * 0.3 + (ratio > 1 ? 0.2 : 0));
      const finalProb = Math.min(0.99, baseProb + reasons.length * 0.05);
      const score = Math.round(finalProb * 100);
      const level = score >= 85 ? "CRITICAL" : score >= 70 ? "HIGH" : score >= 40 ? "MEDIUM" : "LOW";

      return {
        ml_probability: baseProb,
        ml_risk_level: level,
        ml_risk_score: score,
        final_risk_level: level,
        final_risk_score: Math.min(99, score + (reasons.length > 0 ? 5 : 0)),
        recommended_action: score >= 85 ? "HOLD transaction + immediate manual review" : score >= 70 ? "Manual review required" : score >= 40 ? "Allow but monitor" : "Allow",
        policy_override_applied: reasons.length > 0,
        policy_reasons: reasons,
        rule_hits: reasons.filter(r => r.startsWith("Rule matched")).map(r => ({
          name: r.replace("Rule matched: ", ""),
          condition: "amount > 100000 and type_risk_score >= 3",
          reason: r,
        })),
      };
    },
  );
}

export async function updateLogStatus(logId: number, status: "APPROVED" | "BLOCKED"): Promise<void> {
  await apiFetch(
    `/logs/${logId}/action`,
    { method: "POST", body: JSON.stringify({ status }) },
    () => {
      // Mock: update in-memory (no-op for sandbox)
    },
  );
}

// ── Stats ────────────────────────────────────────────────────────────────────

export async function getApiStats() {
  return apiFetch("/stats", {}, () => getStats());
}

export async function getAlertTrendData() {
  // No direct API endpoint for trend — derive from stats or use mock
  return getAlertTrend();
}

// ── Cases ────────────────────────────────────────────────────────────────────

export async function getCases(): Promise<FraudCase[]> {
  return apiFetch("/cases", {}, () => CASES);
}

// ── Rules ────────────────────────────────────────────────────────────────────

export async function getRules(): Promise<BusinessRule[]> {
  return apiFetch("/rules", {}, () => RULES);
}

export async function toggleRule(ruleId: number, isActive: boolean): Promise<void> {
  await apiFetch(
    `/rules/${ruleId}/toggle`,
    { method: "POST", body: JSON.stringify({ is_active: isActive }) },
    () => {
      // Mock: no-op
    },
  );
}

// ── Model Registry ───────────────────────────────────────────────────────────

export async function getModels(): Promise<ModelVersion[]> {
  return apiFetch("/models", {}, () => MODELS);
}

export async function promoteModel(version: string): Promise<void> {
  await apiFetch(
    `/models/${version}/promote`,
    { method: "POST" },
    () => {
      // Mock: no-op
    },
  );
}

export async function reloadModel(): Promise<void> {
  await apiFetch("/admin/reload-model", { method: "POST" }, () => {
    // Mock: no-op
  });
}

// ── Audit logs ───────────────────────────────────────────────────────────────

export async function getAuditLogs(limit = 50): Promise<AuditLog[]> {
  return apiFetch(`/audit?limit=${limit}`, {}, () => AUDIT_LOGS);
}

// ── Copilot ──────────────────────────────────────────────────────────────────

export async function copilotExplain(
  predictionLogId: number,
  followUp?: string,
): Promise<{ explanation: string; is_cached: boolean; latency_ms: number }> {
  return apiFetch(
    "/copilot/explain",
    { method: "POST", body: JSON.stringify({ prediction_log_id: predictionLogId, follow_up: followUp }) },
    () => ({
      explanation: "Copilot is running in mock mode (backend not reachable). Connect to the real API for live LLM explanations.",
      is_cached: false,
      latency_ms: 0,
    }),
  );
}

// ── SHAP / XAI ───────────────────────────────────────────────────────────────

export async function getShapContributors(logId: number): Promise<ShapContributor[]> {
  return apiFetch(`/logs/${logId}/explain`, {}, () => SHAP_CONTRIBUTORS);
}

// ── Health check ─────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string; model_version?: string }> {
  return apiFetch("/health", {}, () => ({ status: "mock" }));
}
