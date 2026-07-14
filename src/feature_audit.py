"""
Feature Leakage Audit Module.

Detects target leakage in engineered features — the #1 cause of inflated ML
metrics that fail to generalize to production. The audit identified in Phase 4
was that PaySim's fraud transactions have deterministic balance rules
(newbalanceOrig=0 for fraud), and engineered features like
`sender_account_emptied` and `balance_error_orig` directly encode these rules.

This module provides three audit strategies:

1. SINGLE_FEATURE_LEAKAGE — check if any single feature perfectly predicts
   the target (correlation = 1.0 or AUC = 1.0). These are smoking guns.

2. DETERMINISTIC_RULE_LEAKAGE — detect features that are deterministic
   functions of the target. For PaySim: fraud TRANSFER/CASH_OUT always has
   newbalanceOrig=0, so any feature computed from newbalanceOrig=0 leaks.

3. PERMUTATION_DROP — train a model with vs without each feature; if removing
   a feature causes AUC to drop by >10%, flag it as suspiciously predictive
   (possibly leaked).

Usage:
    python -m src.feature_audit --data-path transaction_data.csv --output reports/feature_audit.json
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Features flagged in the Phase 4 audit as potential leakage candidates.
# These are deterministic functions of PaySim's fraud-generation rules.
LEAKAGE_SUSPECTS = [
    "sender_account_emptied",          # = 1 iff fraud TRANSFER/CASH_OUT
    "balance_error_orig",              # = 0 iff fraud (deterministic)
    "expected_balance_change_orig",    # derived from newbalanceOrig=0 for fraud
    "balance_change_orig",             # derived from newbalanceOrig=0 for fraud
    "amount_to_oldbalance_orig_ratio", # = 1.0 iff sender_account_emptied
    "dest_received_large_amount",      # destination gets full amount iff fraud
    "is_newbalanceOrig_zero",          # direct proxy for sender_account_emptied
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def audit_single_feature_leakage(
    df: pd.DataFrame, target: str = "isFraud"
) -> List[Dict[str, Any]]:
    """
    Check each feature for perfect single-variable prediction of the target.

    A feature with AUC = 1.0 (or 0.0 — perfectly anti-correlated) is a smoking
    gun for leakage: the model doesn't need to learn anything, it just reads
    the answer off one column.
    """
    findings: List[Dict[str, Any]] = []
    y = df[target]

    for col in df.columns:
        if col == target:
            continue
        try:
            x = df[col].astype(float)
        except (ValueError, TypeError):
            continue

        # Skip constant columns
        if x.nunique() < 2:
            continue

        try:
            auc = roc_auc_score(y, x)
        except ValueError:
            continue

        # AUC near 0 or 1 means perfect (anti-)prediction
        leak_score = max(auc, 1 - auc)
        if leak_score >= 0.999:
            findings.append({
                "feature": col,
                "auc": float(auc),
                "leak_score": float(leak_score),
                "severity": "CRITICAL",
                "reason": f"Single feature AUC = {auc:.4f} — perfect target prediction",
            })
        elif leak_score >= 0.95:
            findings.append({
                "feature": col,
                "auc": float(auc),
                "leak_score": float(leak_score),
                "severity": "HIGH",
                "reason": f"Single feature AUC = {auc:.4f} — near-perfect target prediction",
            })

    return findings


def audit_deterministic_rules(
    df: pd.DataFrame, target: str = "isFraud"
) -> List[Dict[str, Any]]:
    """
    Detect features that are deterministic functions of the target by checking
    if the feature value distribution is degenerate conditioned on the target.

    If feature X always equals value V when target=1, and never equals V when
    target=0, then X is a leaked proxy for the target.
    """
    findings: List[Dict[str, Any]] = []
    y = df[target]

    for col in LEAKAGE_SUSPECTS:
        if col not in df.columns:
            continue
        try:
            x = df[col].astype(float)
        except (ValueError, TypeError):
            continue

        fraud_vals = x[y == 1]
        legit_vals = x[y == 0]

        if len(fraud_vals) == 0 or len(legit_vals) == 0:
            continue

        # Check: does the feature have a degenerate distribution in fraud?
        fraud_mode = fraud_vals.mode()
        if len(fraud_mode) == 0:
            continue
        mode_val = fraud_mode.iloc[0]
        fraud_mode_frac = (fraud_vals == mode_val).mean()
        legit_mode_frac = (legit_vals == mode_val).mean()

        # If >95% of fraud has this value but <5% of legit does → leaked
        if fraud_mode_frac > 0.95 and legit_mode_frac < 0.05:
            findings.append({
                "feature": col,
                "mode_value": float(mode_val),
                "fraud_mode_fraction": float(fraud_mode_frac),
                "legit_mode_fraction": float(legit_mode_frac),
                "severity": "CRITICAL",
                "reason": (
                    f"{fraud_mode_frac*100:.1f}% of fraud has {col}={mode_val}, "
                    f"but only {legit_mode_frac*100:.1f}% of legitimate does — "
                    f"deterministic target proxy"
                ),
            })

    return findings


def audit_permutation_drop(
    df: pd.DataFrame,
    target: str = "isFraud",
    sample_size: int = 50_000,
    random_state: int = 42,
) -> List[Dict[str, Any]]:
    """
    Train a baseline RandomForest, then retrain with each feature removed.
    Features whose removal causes AUC to drop by >10% are flagged as
    suspiciously predictive (may be leaked).

    This is expensive (O(n_features) model trainings) so we sample the data.
    """
    findings: List[Dict[str, Any]] = []

    # Sample for speed
    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=random_state)

    y = df[target]
    X = df.drop(columns=[target, "isFlaggedFraud"], errors="ignore")
    # Drop non-numeric columns
    X = X.select_dtypes(include=[np.number])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    # Baseline
    baseline_clf = RandomForestClassifier(
        n_estimators=50, max_depth=8, random_state=random_state, n_jobs=1
    )
    baseline_clf.fit(X_train, y_train)
    baseline_auc = roc_auc_score(
        y_test, baseline_clf.predict_proba(X_test)[:, 1]
    )

    # Drop-one-feature
    for col in X.columns:
        X_train_drop = X_train.drop(columns=[col])
        X_test_drop = X_test.drop(columns=[col])

        clf = RandomForestClassifier(
            n_estimators=50, max_depth=8, random_state=random_state, n_jobs=1
        )
        clf.fit(X_train_drop, y_train)
        auc = roc_auc_score(y_test, clf.predict_proba(X_test_drop)[:, 1])

        drop = baseline_auc - auc
        if drop > 0.10:  # >10% AUC drop = suspiciously predictive
            findings.append({
                "feature": col,
                "baseline_auc": float(baseline_auc),
                "auc_without_feature": float(auc),
                "auc_drop": float(drop),
                "severity": "HIGH" if drop > 0.20 else "MEDIUM",
                "reason": (
                    f"Removing {col} drops AUC by {drop*100:.1f}% "
                    f"({baseline_auc:.4f} → {auc:.4f})"
                ),
            })

    return sorted(findings, key=lambda f: f["auc_drop"], reverse=True)


def run_full_audit(
    data_path: Path,
    output_path: Optional[Path] = None,
    skip_permutation: bool = False,
) -> Dict[str, Any]:
    """
    Run all three leakage audits and return a consolidated report.
    """
    logger.info("Loading data from %s...", data_path)
    df = pd.read_csv(data_path, nrows=200_000)  # cap for speed

    # Build the same engineered features as the training pipeline
    from src.features import build_features, load_feature_config

    config = load_feature_config()
    feature_rows = []
    for _, row in df.iterrows():
        tx = {
            "step": int(row["step"]),
            "type": str(row["type"]),
            "amount": float(row["amount"]),
            "oldbalanceOrg": float(row["oldbalanceOrg"]),
            "newbalanceOrig": float(row["newbalanceOrig"]),
            "oldbalanceDest": float(row["oldbalanceDest"]),
            "newbalanceDest": float(row["newbalanceDest"]),
        }
        X = build_features(tx, config)
        feature_rows.append(X.iloc[0].to_dict())

    feature_df = pd.DataFrame(feature_rows)
    feature_df["isFraud"] = df["isFraud"].values

    logger.info("Running single-feature leakage audit...")
    single = audit_single_feature_leakage(feature_df)

    logger.info("Running deterministic-rule audit...")
    deterministic = audit_deterministic_rules(feature_df)

    permutation: List[Dict[str, Any]] = []
    if not skip_permutation:
        logger.info("Running permutation-drop audit (this takes a few minutes)...")
        permutation = audit_permutation_drop(feature_df)

    report = {
        "audit_date": _now(),
        "data_path": str(data_path),
        "sample_size": len(feature_df),
        "fraud_rate": float(feature_df["isFraud"].mean()),
        "single_feature_leakage": single,
        "deterministic_rule_leakage": deterministic,
        "permutation_drop": permutation,
        "summary": {
            "critical_count": sum(
                1 for f in single + deterministic if f["severity"] == "CRITICAL"
            ),
            "high_count": sum(
                1 for f in single + deterministic + permutation
                if f["severity"] == "HIGH"
            ),
            "recommendation": _build_recommendation(single, deterministic),
        },
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("Audit report written to %s", output_path)

    return report


def _build_recommendation(
    single: List[Dict[str, Any]], deterministic: List[Dict[str, Any]]
) -> str:
    """Generate a human-readable recommendation based on the audit findings."""
    critical = [f for f in single + deterministic if f["severity"] == "CRITICAL"]
    if not critical:
        return "No critical leakage detected. Monitor features in production via drift checks."

    feature_names = sorted({f["feature"] for f in critical})
    return (
        f"CRITICAL leakage detected in {len(feature_names)} feature(s): "
        f"{', '.join(feature_names)}. These features are deterministic functions "
        f"of the target and must be removed or re-engineered before the model "
        f"can be trusted in production. AUC=0.9998 is inflated by this leakage "
        f"and will NOT generalize to real-world fraud."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Audit features for target leakage")
    parser.add_argument("--data-path", type=Path, default=PROJECT_ROOT / "transaction_data.csv")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "feature_audit.json")
    parser.add_argument("--skip-permutation", action="store_true", help="Skip the expensive permutation-drop audit")
    args = parser.parse_args()

    report = run_full_audit(args.data_path, args.output, skip_permutation=args.skip_permutation)
    print(json.dumps(report["summary"], indent=2))
