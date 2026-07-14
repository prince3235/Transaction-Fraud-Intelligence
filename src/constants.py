"""
Shared constants for the Transaction Fraud Intelligence Platform.

Centralizes thresholds and configuration that were previously scattered across
modules (drift_monitor used 0.2, retrain_trigger used 0.25 — now unified).
"""
from __future__ import annotations

# ── Drift / PSI thresholds ────────────────────────────────────────────────────
# Industry-standard PSI interpretation:
#   PSI < 0.1  → no significant drift
#   0.1 ≤ PSI < 0.25 → moderate drift (warn, monitor closely)
#   PSI ≥ 0.25 → significant drift (trigger retrain review)
PSI_NO_DRIFT = 0.1
PSI_MODERATE_DRIFT = 0.25
PSI_SIGNIFICANT_DRIFT = 0.25  # trigger threshold (kept explicit for clarity)

# Unified alias — both drift_monitor and retrain_trigger import from here.
DRIFT_THRESHOLD = PSI_SIGNIFICANT_DRIFT
ALERT_THRESHOLD = PSI_MODERATE_DRIFT

# ── Retrain gating ────────────────────────────────────────────────────────────
# A candidate model must beat the current production model by at least this
# much on PR-AUC before it's allowed to overwrite the prod pkl.
MIN_METRIC_IMPROVEMENT = 0.002  # 0.2% absolute improvement required
RETRAIN_EVAL_METRIC = "pr_auc"  # primary metric for champion/challenger

# ── Model versioning ──────────────────────────────────────────────────────────
MAX_MODEL_VERSIONS_RETAINED = 50  # soft cap; older auto-archived

# ── Drift check schedule ─────────────────────────────────────────────────────
DRIFT_CHECK_INTERVAL_MINUTES = 30  # was 5 (too aggressive for real retrain)
BASELINE_SAMPLE_SIZE = 5000        # rows sampled from training set for baseline
CURRENT_SAMPLE_SIZE = 1000         # rows sampled from recent prediction_logs

# ── Features monitored for drift ─────────────────────────────────────────────
# These are the engineered features most likely to drift in production.
DRIFT_FEATURES = [
    "amount",
    "log_amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "balance_error_orig",
    "amount_to_oldbalance_orig_ratio",
    "suspicious_signal_count",
    "type_risk_score",
]
