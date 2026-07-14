/**
 * Mock data layer for the Transaction Fraud Intelligence Platform.
 *
 * In production, these types and data would come from the FastAPI backend at
 * /predict, /alerts, /cases, /copilot/*, /stats. For the standalone preview,
 * we provide realistic synthetic data with the same shape as the API responses
 * so the UI renders identically when wired to a real backend.
 */

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type TxStatus = "PENDING_REVIEW" | "APPROVED" | "BLOCKED" | "ESCALATED";
export type TxType = "TRANSFER" | "CASH_OUT" | "PAYMENT" | "DEBIT" | "CASH_IN";

export interface PredictionLog {
  id: number;
  created_at: string;
  transaction: {
    step: number;
    type: TxType;
    amount: number;
    nameOrig: string;
    nameDest: string;
    oldbalanceOrg: number;
    newbalanceOrig: number;
    oldbalanceDest: number;
    newbalanceDest: number;
  };
  ml_probability: number;
  ml_risk_level: RiskLevel;
  ml_risk_score: number;
  final_risk_level: RiskLevel;
  final_risk_score: number;
  policy_override_applied: boolean;
  policy_reasons: string[];
  rule_hits?: { name: string; condition: string; reason: string }[];
  suspicious_signal_count: number;
  status: TxStatus;
  assigned_to?: string | null;
  case_id?: string | null;
}

export interface FraudCase {
  id: string;
  case_id: string;
  prediction_log_id: number;
  status: "OPEN" | "INVESTIGATING" | "ESCALATED" | "RESOLVED";
  priority: "P1" | "P2" | "P3";
  assigned_to: string | null;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  risk_level: RiskLevel;
  amount: number;
  notes: {
    id: number;
    author: string;
    content: string;
    timestamp: string;
  }[];
  timeline: {
    id: number;
    timestamp: string;
    actor: string;
    action: string;
    note?: string;
  }[];
}

export interface BusinessRule {
  id: number;
  name: string;
  description: string;
  rule_type: "AMOUNT" | "VELOCITY" | "PATTERN" | "GEO" | "BALANCE";
  condition: string;
  action: "flag" | "escalate" | "block";
  risk_level_bump: RiskLevel;
  priority: number;
  is_active: boolean;
  triggered_count: number;
  created_at: string;
}

export interface ModelVersion {
  id: number;
  version: string;
  pkl_path: string;
  roc_auc: number;
  pr_auc: number;
  precision: number;
  recall: number;
  f1: number;
  n_estimators: number;
  training_date: string;
  dataset_size: number;
  feature_count: number;
  notes: string;
  is_production: boolean;
  is_archived: boolean;
  created_at: string;
}

export interface AuditLog {
  id: number;
  username: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  old_value: unknown;
  new_value: unknown;
  ip_address: string;
  reason: string | null;
  timestamp: string;
}

export interface ShapContributor {
  feature: string;
  value: number;
  contribution: number;
  direction: "positive" | "negative";
}

// ──────────────────────────────────────────────────────────────────────────
// Synthetic data generators
// ──────────────────────────────────────────────────────────────────────────

const CUSTOMERS = [
  "C-4827361", "C-2918473", "C-7263948", "C-1038472", "C-5829374",
  "C-9182736", "C-3748291", "C-6253748", "C-8293746", "C-4728391",
  "C-1938475", "C-6384920", "C-5829373", "C-9283746", "C-3849502",
];

const MERCHANTS = [
  "Acme Corp", "Globex LLC", "CryptoBay Exchange", "Nimbus Pay",
  "Vertex Trading", "Pinnacle Bank", "Quantum Wallet", "Orbit Finance",
  "Helix Gaming", "Zenith Travel",
];

function rand<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}
function randInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}
function randFloat(min: number, max: number, decimals = 2): number {
  const v = Math.random() * (max - min) + min;
  return parseFloat(v.toFixed(decimals));
}
function isoMinusHours(h: number): string {
  return new Date(Date.now() - h * 3600_000).toISOString();
}
function isoMinusDays(d: number): string {
  return new Date(Date.now() - d * 86_400_000).toISOString();
}

function pickRisk(): { level: RiskLevel; score: number; prob: number } {
  const r = Math.random();
  if (r > 0.93) return { level: "CRITICAL", score: randInt(86, 99), prob: randFloat(0.86, 0.99, 4) };
  if (r > 0.80) return { level: "HIGH", score: randInt(70, 85), prob: randFloat(0.70, 0.85, 4) };
  if (r > 0.55) return { level: "MEDIUM", score: randInt(40, 69), prob: randFloat(0.40, 0.69, 4) };
  return { level: "LOW", score: randInt(1, 39), prob: randFloat(0.01, 0.39, 4) };
}

const REASON_POOL = [
  "Policy: Amount > sender balance + sender account emptied",
  "Policy: Multiple suspicious signals detected (>=3)",
  "Policy: Very high suspicious signal count (>=5)",
  "Policy: Large transaction + destination started from zero balance",
  "Rule matched: High-velocity transfer pattern",
  "Rule matched: Impossible travel detected",
  "Rule matched: Cash-out after transfer within 1h",
  "Rule matched: First-time high-value destination",
  "Rule matched: Round-amount pattern ($10k / $50k / $100k)",
  "Rule matched: Beneficiary balance anomaly",
];

function buildTx(i: number, opts: Partial<PredictionLog> = {}): PredictionLog {
  const risk = pickRisk();
  const type = rand<TxType>(["TRANSFER", "CASH_OUT", "PAYMENT", "DEBIT", "CASH_IN"]);
  const sender = rand(CUSTOMERS);
  const recipient = rand(CUSTOMERS.filter((c) => c !== sender));
  const amount =
    risk.level === "CRITICAL" ? randFloat(80_000, 9_000_000) :
    risk.level === "HIGH" ? randFloat(15_000, 250_000) :
    risk.level === "MEDIUM" ? randFloat(2_500, 40_000) :
    randFloat(50, 5_000);

  const oldBalOrg = randFloat(amount * 0.8, amount * 1.5);
  const newBalOrg = Math.max(0, oldBalOrg - amount);
  const oldBalDest = randFloat(0, 100_000);
  const newBalDest = oldBalDest + amount;

  const reasons =
    risk.level === "LOW" ? [] :
    Array.from({ length: randInt(1, 3) }, () => rand(REASON_POOL));

  const ruleHits = reasons
    .filter((r) => r.startsWith("Rule matched"))
    .map((r) => ({
      name: r.replace("Rule matched: ", ""),
      condition: "amount > 100000 and type_risk_score >= 3",
      reason: r,
    }));

  const statusPool: TxStatus[] =
    risk.level === "CRITICAL" || risk.level === "HIGH"
      ? ["PENDING_REVIEW", "ESCALATED", "BLOCKED"]
      : risk.level === "MEDIUM"
      ? ["PENDING_REVIEW", "APPROVED"]
      : ["APPROVED"];

  return {
    id: i + 1,
    created_at: isoMinusHours(randInt(0, 168)),
    transaction: {
      step: randInt(1, 743),
      type,
      amount,
      nameOrig: sender,
      nameDest: recipient,
      oldbalanceOrg: oldBalOrg,
      newbalanceOrig: newBalOrg,
      oldbalanceDest: oldBalDest,
      newbalanceDest: newBalDest,
    },
    ml_probability: risk.prob,
    ml_risk_level: risk.level,
    ml_risk_score: risk.score,
    final_risk_level: risk.level,
    final_risk_score: Math.min(99, risk.score + (reasons.length > 0 ? 5 : 0)),
    policy_override_applied: reasons.length > 0,
    policy_reasons: reasons,
    rule_hits: ruleHits,
    suspicious_signal_count:
      risk.level === "CRITICAL" ? randInt(5, 6) :
      risk.level === "HIGH" ? randInt(3, 5) :
      risk.level === "MEDIUM" ? randInt(1, 3) :
      randInt(0, 1),
    status: rand(statusPool),
    assigned_to: risk.level === "CRITICAL" || risk.level === "HIGH" ? rand(["A.Patel", "R.Singh", "M.Khan", "S.Verma"]) : null,
    case_id: risk.level === "CRITICAL" || risk.level === "HIGH" ? `FCS-2025-${String(randInt(100, 999)).padStart(6, "0")}` : null,
    ...opts,
  };
}

export const ALERTS: PredictionLog[] = Array.from({ length: 80 }, (_, i) => buildTx(i));

export const RECENT_TICKER_ALERTS: PredictionLog[] = ALERTS
  .slice()
  .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at))
  .slice(0, 12);

// ──────────────────────────────────────────────────────────────────────────
// Cases
// ──────────────────────────────────────────────────────────────────────────

const CASE_TITLES = [
  "High-velocity TRANSFER → CASH_OUT chain",
  "Account drain via rapid TRANSFER bursts",
  "Impossible travel: transaction 8,500mi apart in 4min",
  "Round-amount CASH_OUT to first-time beneficiary",
  "Multiple failed login → large transfer",
  "New device + first-time high-value destination",
  "Balance anomaly: sender balance mismatch",
  "Beneficiary received $1M from 7 senders in 10min",
  "Crypto exchange cash-out flagged by velocity rule",
  "Off-hours CASH_OUT with empty destination prior",
];

export const CASES: FraudCase[] = Array.from({ length: 18 }, (_, i) => {
  const status = rand<FraudCase["status"]>(["OPEN", "INVESTIGATING", "ESCALATED", "RESOLVED"]);
  const priority = rand<FraudCase["priority"]>(["P1", "P2", "P3"]);
  const risk = pickRisk();
  const amount =
    risk.level === "CRITICAL" ? randFloat(200_000, 5_000_000) :
    risk.level === "HIGH" ? randFloat(50_000, 500_000) :
    randFloat(10_000, 100_000);
  const createdAt = isoMinusDays(randInt(0, 14));
  return {
    id: `case-${i + 1}`,
    case_id: `FCS-2025-${String(randInt(100, 999)).padStart(6, "0")}`,
    prediction_log_id: randInt(1, 80),
    status,
    priority,
    assigned_to: status === "OPEN" ? null : rand(["A.Patel", "R.Singh", "M.Khan", "S.Verma"]),
    title: rand(CASE_TITLES),
    description: `Transaction ${randInt(1000, 9999)} from ${rand(CUSTOMERS)} to ${rand(MERCHANTS)} flagged by ${rand(REASON_POOL).replace("Policy: ", "").replace("Rule matched: ", "")} pattern. Manual review required to confirm intent.`,
    created_at: createdAt,
    updated_at: isoMinusHours(randInt(0, 48)),
    resolved_at: status === "RESOLVED" ? isoMinusHours(randInt(0, 24)) : null,
    risk_level: risk.level,
    amount,
    notes: Array.from({ length: randInt(0, 4) }, (_, j) => ({
      id: j + 1,
      author: rand(["A.Patel", "R.Singh", "M.Khan", "S.Verma"]),
      content: rand([
        "Reviewed KYC documents — account verified 2 months ago, no prior flags.",
        "Contacted customer via phone — confirmed transaction is legitimate.",
        "Pattern matches known fraud ring targeting crypto exchanges.",
        "Need to check velocity against historical baseline before escalation.",
        "Customer reports device was compromised; freezing account pending SOC review.",
      ]),
      timestamp: isoMinusHours(randInt(1, 72)),
    })),
    timeline: [
      {
        id: 1,
        timestamp: createdAt,
        actor: "system",
        action: "Case created",
        note: "Auto-created from PENDING_REVIEW alert",
      },
      ...(status !== "OPEN" ? [{
        id: 2,
        timestamp: isoMinusHours(randInt(20, 40)),
        actor: rand(["A.Patel", "R.Singh"]),
        action: "Status changed to INVESTIGATING",
      }] : []),
      ...(status === "ESCALATED" || status === "RESOLVED" ? [{
        id: 3,
        timestamp: isoMinusHours(randInt(8, 18)),
        actor: rand(["M.Khan", "S.Verma"]),
        action: "Case escalated to L2 review",
        note: "Pattern consistent with fraud ring; needs SOC escalation",
      }] : []),
      ...(status === "RESOLVED" ? [{
        id: 4,
        timestamp: isoMinusHours(randInt(0, 6)),
        actor: "system",
        action: "Case resolved",
        note: rand([
          "Transaction blocked — confirmed fraud.",
          "Transaction approved — customer confirmed legitimate.",
          "Customer refunded; account secured with new credentials.",
        ]),
      }] : []),
    ],
  };
});

// ──────────────────────────────────────────────────────────────────────────
// Business rules
// ──────────────────────────────────────────────────────────────────────────

export const RULES: BusinessRule[] = [
  {
    id: 1,
    name: "Large Transfer Amount",
    description: "Flags any TRANSFER transaction above $100,000 for manual review.",
    rule_type: "AMOUNT",
    condition: "amount > 100000 and type_encoded == 4",
    action: "flag",
    risk_level_bump: "HIGH",
    priority: 90,
    is_active: true,
    triggered_count: 1247,
    created_at: isoMinusDays(45),
  },
  {
    id: 2,
    name: "Account Drain Pattern",
    description: "Detects when a transaction empties the sender's account balance entirely.",
    rule_type: "BALANCE",
    condition: "sender_account_emptied == 1 and amount_to_oldbalance_orig_ratio > 0.95",
    action: "block",
    risk_level_bump: "CRITICAL",
    priority: 100,
    is_active: true,
    triggered_count: 89,
    created_at: isoMinusDays(45),
  },
  {
    id: 3,
    name: "High Velocity Window",
    description: "Flags accounts with more than 5 transactions in a single step (1 hour).",
    rule_type: "VELOCITY",
    condition: "transactions_in_step > 5 and is_high_velocity_step == 1",
    action: "escalate",
    risk_level_bump: "HIGH",
    priority: 85,
    is_active: true,
    triggered_count: 412,
    created_at: isoMinusDays(45),
  },
  {
    id: 4,
    name: "First-time Beneficiary + Large Amount",
    description: "Large transfer to a destination the sender has never transacted with.",
    rule_type: "PATTERN",
    condition: "is_large_transaction == 1 and dest_received_large_amount == 1",
    action: "flag",
    risk_level_bump: "MEDIUM",
    priority: 70,
    is_active: true,
    triggered_count: 1823,
    created_at: isoMinusDays(45),
  },
  {
    id: 5,
    name: "Balance Error Anomaly",
    description: "Mathematical balance inconsistency — suggests tampering or data corruption.",
    rule_type: "BALANCE",
    condition: "balance_error_orig != 0 and amount > 10000",
    action: "escalate",
    risk_level_bump: "HIGH",
    priority: 75,
    is_active: true,
    triggered_count: 234,
    created_at: isoMinusDays(45),
  },
  {
    id: 6,
    name: "Round Amount Pattern",
    description: "Suspiciously round amounts ($10k / $50k / $100k) often used in layering.",
    rule_type: "PATTERN",
    condition: "amount in [10000, 50000, 100000, 500000, 1000000]",
    action: "flag",
    risk_level_bump: "MEDIUM",
    priority: 60,
    is_active: true,
    triggered_count: 982,
    created_at: isoMinusDays(30),
  },
  {
    id: 7,
    name: "Multiple Suspicious Signals",
    description: "When 3+ suspicious signals combine, escalate regardless of ML score.",
    rule_type: "PATTERN",
    condition: "suspicious_signal_count >= 3",
    action: "escalate",
    risk_level_bump: "HIGH",
    priority: 80,
    is_active: true,
    triggered_count: 567,
    created_at: isoMinusDays(30),
  },
  {
    id: 8,
    name: "Severe Signal Cluster",
    description: "5+ suspicious signals indicate near-certain fraud — auto-block.",
    rule_type: "PATTERN",
    condition: "suspicious_signal_count >= 5",
    action: "block",
    risk_level_bump: "CRITICAL",
    priority: 95,
    is_active: false,
    triggered_count: 23,
    created_at: isoMinusDays(15),
  },
];

// ──────────────────────────────────────────────────────────────────────────
// Model registry
// ──────────────────────────────────────────────────────────────────────────

export const MODELS: ModelVersion[] = [
  {
    id: 4,
    version: "v4",
    pkl_path: "models/best_fraud_model.pkl",
    roc_auc: 0.9991,
    pr_auc: 0.9968,
    precision: 0.9823,
    recall: 0.9741,
    f1: 0.9782,
    n_estimators: 200,
    training_date: isoMinusDays(2),
    dataset_size: 6_362_620,
    feature_count: 29,
    notes: "Retrained with temporal split (steps 1-600 train, 601-743 test). Calibrated via isotonic regression.",
    is_production: true,
    is_archived: false,
    created_at: isoMinusDays(2),
  },
  {
    id: 3,
    version: "v3",
    pkl_path: "models/v3_fraud_model.pkl",
    roc_auc: 0.9987,
    pr_auc: 0.9954,
    precision: 0.9798,
    recall: 0.9698,
    f1: 0.9748,
    n_estimators: 200,
    training_date: isoMinusDays(15),
    dataset_size: 6_362_620,
    feature_count: 29,
    notes: "Added step_bucket + velocity features. Threshold tuned on validation set (not test).",
    is_production: false,
    is_archived: false,
    created_at: isoMinusDays(15),
  },
  {
    id: 2,
    version: "v2",
    pkl_path: "models/v2_fraud_model.pkl",
    roc_auc: 0.9972,
    pr_auc: 0.9912,
    precision: 0.9654,
    recall: 0.9587,
    f1: 0.9620,
    n_estimators: 150,
    training_date: isoMinusDays(35),
    dataset_size: 5_800_000,
    feature_count: 25,
    notes: "Replaced manual undersampling with class_weight='balanced_subsample'.",
    is_production: false,
    is_archived: true,
    created_at: isoMinusDays(35),
  },
  {
    id: 1,
    version: "v1",
    pkl_path: "models/v1_fraud_model.pkl",
    roc_auc: 0.9941,
    pr_auc: 0.9823,
    precision: 0.9341,
    recall: 0.8876,
    f1: 0.9103,
    n_estimators: 50,
    training_date: isoMinusDays(60),
    dataset_size: 1_000_000,
    feature_count: 21,
    notes: "Initial baseline model. Random split (no temporal). Served as MVP.",
    is_production: false,
    is_archived: true,
    created_at: isoMinusDays(60),
  },
];

// ──────────────────────────────────────────────────────────────────────────
// Audit logs
// ──────────────────────────────────────────────────────────────────────────

const AUDIT_ACTIONS = [
  { action: "User Login", entity_type: "auth" },
  { action: "Rule Created", entity_type: "business_rule" },
  { action: "Rule Toggled", entity_type: "business_rule" },
  { action: "Model Promoted", entity_type: "model_registry" },
  { action: "Model Archived", entity_type: "model_registry" },
  { action: "Case Status Changed", entity_type: "fraud_case" },
  { action: "Note Added", entity_type: "fraud_case" },
  { action: "Case Assigned", entity_type: "fraud_case" },
  { action: "Transaction Blocked", entity_type: "prediction_log" },
  { action: "Transaction Approved", entity_type: "prediction_log" },
  { action: "Copilot Query", entity_type: "llm_copilot" },
  { action: "Export Generated", entity_type: "export" },
];

const USERNAMES = ["admin", "a.patel", "r.singh", "m.khan", "s.verma", "compliance", "auditor"];

export const AUDIT_LOGS: AuditLog[] = Array.from({ length: 50 }, (_, i) => {
  const a = rand(AUDIT_ACTIONS);
  return {
    id: i + 1,
    username: rand(USERNAMES),
    action: a.action,
    entity_type: a.entity_type,
    entity_id: randInt(1, 100).toString(),
    old_value: i % 3 === 0 ? { status: "OPEN" } : null,
    new_value: i % 3 === 0 ? { status: "INVESTIGATING" } : { value: randInt(1, 1000) },
    ip_address: `10.0.${randInt(0, 255)}.${randInt(1, 254)}`,
    reason: i % 4 === 0 ? rand(["Routine review", "Customer escalation", "SLA breach risk", "Pattern match"]) : null,
    timestamp: isoMinusHours(randInt(0, 168)),
  };
});

// ──────────────────────────────────────────────────────────────────────────
// SHAP contributors (for case detail XAI panel)
// ──────────────────────────────────────────────────────────────────────────

export const SHAP_CONTRIBUTORS: ShapContributor[] = [
  { feature: "balance_error_orig", value: 0.0, contribution: 0.1843, direction: "positive" },
  { feature: "sender_account_emptied", value: 1.0, contribution: 0.1421, direction: "positive" },
  { feature: "amount_to_oldbalance_orig_ratio", value: 1.0, contribution: 0.0987, direction: "positive" },
  { feature: "transactions_in_step", value: 16.0, contribution: 0.0742, direction: "positive" },
  { feature: "expected_balance_change_orig", value: 0.0, contribution: 0.0663, direction: "positive" },
  { feature: "is_large_transaction", value: 1.0, contribution: 0.0512, direction: "positive" },
  { feature: "log_amount", value: 11.51, contribution: 0.0438, direction: "positive" },
  { feature: "suspicious_signal_count", value: 5.0, contribution: 0.0411, direction: "positive" },
  { feature: "type_risk_score", value: 3.0, contribution: 0.0387, direction: "positive" },
  { feature: "dest_received_large_amount", value: 1.0, contribution: 0.0294, direction: "positive" },
];

// ──────────────────────────────────────────────────────────────────────────
// Aggregated stats (for command center)
// ──────────────────────────────────────────────────────────────────────────

export function getStats() {
  const total = ALERTS.length;
  const byLevel = (lvl: RiskLevel) => ALERTS.filter((a) => a.final_risk_level === lvl).length;
  const byStatus = (s: TxStatus) => ALERTS.filter((a) => a.status === s).length;
  const overrideRate = (ALERTS.filter((a) => a.policy_override_applied).length / total) * 100;
  const avgScore = ALERTS.reduce((sum, a) => sum + a.final_risk_score, 0) / total;
  const totalAmount = ALERTS.reduce((s, a) => s + a.transaction.amount, 0);
  const blockedAmount = ALERTS
    .filter((a) => a.status === "BLOCKED")
    .reduce((s, a) => s + a.transaction.amount, 0);
  const potentialLoss = ALERTS
    .filter((a) => a.status === "APPROVED" && (a.final_risk_level === "HIGH" || a.final_risk_level === "CRITICAL"))
    .reduce((s, a) => s + a.transaction.amount, 0);

  return {
    total,
    critical: byLevel("CRITICAL"),
    high: byLevel("HIGH"),
    medium: byLevel("MEDIUM"),
    low: byLevel("LOW"),
    pending: byStatus("PENDING_REVIEW"),
    approved: byStatus("APPROVED"),
    blocked: byStatus("BLOCKED"),
    escalated: byStatus("ESCALATED"),
    overrideRate: parseFloat(overrideRate.toFixed(1)),
    avgScore: parseFloat(avgScore.toFixed(1)),
    totalAmount,
    blockedAmount,
    potentialLoss,
    cases: CASES.length,
    openCases: CASES.filter((c) => c.status === "OPEN" || c.status === "INVESTIGATING").length,
  };
}

export function getAlertTrend(): { date: string; alerts: number; blocked: number }[] {
  const out: { date: string; alerts: number; blocked: number }[] = [];
  for (let d = 13; d >= 0; d--) {
    const date = new Date(Date.now() - d * 86_400_000);
    out.push({
      date: date.toISOString().slice(0, 10),
      alerts: randInt(40, 120),
      blocked: randInt(8, 35),
    });
  }
  return out;
}

// ──────────────────────────────────────────────────────────────────────────
// Copilot mock streaming response
// ──────────────────────────────────────────────────────────────────────────

export const COPILOT_RESPONSE = `This transaction exhibits a classic account-drain fraud pattern.

The ML model assigned a 99.7% fraud probability, driven primarily by:
1. balance_error_orig = 0.0 — the sender's new balance perfectly matches the expected balance after deduction, a deterministic signature of PaySim-simulated fraud.
2. sender_account_emptied = 1 — the entire oldbalanceOrg ($1,250,000) was transferred out, leaving newbalanceOrig at $0.
3. amount_to_oldbalance_orig_ratio = 1.0 — transaction amount equals the entire sender balance.

The Rules Engine escalated this from HIGH to CRITICAL via the "Account Drain Pattern" rule (priority 100), which auto-blocks transactions where sender_account_emptied == 1 AND amount_to_oldbalance_orig_ratio > 0.95.

Recommended action: HOLD transaction + immediate manual review. Consider freezing the sender account pending KYC re-verification.

[RECOMMEND_ESCALATION]`;
