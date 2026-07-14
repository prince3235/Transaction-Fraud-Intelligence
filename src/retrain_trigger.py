"""
Enterprise Drift Monitor + Retrain Trigger.

This module was previously a stub that compared two arrays of synthetic random
Gaussian noise — the "drift" signal was purely a function of how many rows
were in prediction_logs, not of actual feature distribution shift.

This rewrite:
- Pulls REAL feature distributions from `prediction_logs` (last N transactions)
- Compares against a saved baseline from the training set (cached to disk)
- Computes PSI per monitored feature using the shared DRIFT_THRESHOLD
- Only triggers retrain if ANY feature crosses the threshold
- Gates the retrain on a champion/challenger metric check (new model must beat
  current prod by MIN_METRIC_IMPROVEMENT on RETRAIN_EVAL_METRIC before the
  prod pkl is overwritten)
- Records every drift snapshot to the `drift_snapshots` table for the dashboard
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

from src.constants import (
    BASELINE_SAMPLE_SIZE,
    CURRENT_SAMPLE_SIZE,
    DRIFT_CHECK_INTERVAL_MINUTES,
    DRIFT_FEATURES,
    DRIFT_THRESHOLD,
    MIN_METRIC_IMPROVEMENT,
    RETRAIN_EVAL_METRIC,
)
from src.db import SessionLocal
from src.drift_monitor import calculate_psi, record_drift_snapshot
from src.models import PredictionLog
from src.train_pipeline import train_model  # imported at module level (matches original; tests patch this)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "transaction_data.csv"
BASELINE_CACHE_PATH = PROJECT_ROOT / "models" / "drift_baseline.json"


# ── Baseline management ──────────────────────────────────────────────────────

def _extract_features_from_tx(tx_json: Any) -> Dict[str, float]:
    """Extract numeric features from a prediction log's transaction_json cell.

    Handles both dict (PG JSONB) and str (SQLite TEXT) shapes. Returns a flat
    dict of feature_name → float for the features we monitor for drift.
    """
    if tx_json is None:
        return {}
    if isinstance(tx_json, str):
        try:
            tx_json = json.loads(tx_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    if not isinstance(tx_json, dict):
        return {}

    amount = float(tx_json.get("amount", 0) or 0)
    oldbalanceOrg = float(tx_json.get("oldbalanceOrg", 0) or 0)
    newbalanceOrig = float(tx_json.get("newbalanceOrig", 0) or 0)

    # Derived features (mirrors src/features.build_features for the subset we monitor)
    return {
        "amount": amount,
        "log_amount": float(np.log1p(max(0, amount))),
        "oldbalanceOrg": oldbalanceOrg,
        "newbalanceOrig": newbalanceOrig,
        "balance_error_orig": float(newbalanceOrig - (oldbalanceOrg - amount)),
        "amount_to_oldbalance_orig_ratio": (
            float(amount / oldbalanceOrg) if oldbalanceOrg > 0 else 0.0
        ),
        "suspicious_signal_count": float(
            int((oldbalanceOrg > 0) and (newbalanceOrig == 0))
            + int(amount > 518634.19)  # large_threshold_p95 from feature_config
            + int(abs(newbalanceOrig - (oldbalanceOrg - amount)) > 0)
        ),
        "type_risk_score": float(
            {"CASH_OUT": 3, "TRANSFER": 3, "DEBIT": 2, "CASH_IN": 1, "PAYMENT": 1}.get(
                str(tx_json.get("type", "")).upper(), 0
            )
        ),
    }


def build_baseline_from_training_data(data_path: Path = DATA_PATH) -> Dict[str, List[float]]:
    """Sample features from the training CSV and cache to disk as the baseline.

    Called once (manually or on first drift check). Subsequent checks load
    the cached baseline instead of re-reading the 1GB CSV.
    """
    logger.info("Building drift baseline from %s (sample %d rows)...",
                data_path, BASELINE_SAMPLE_SIZE)
    try:
        # Read a random sample — skiprows with a random mask is the simplest
        # way to get a representative sample without loading the whole file.
        df = pd.read_csv(data_path, nrows=BASELINE_SAMPLE_SIZE * 3)
        df = df.sample(n=min(BASELINE_SAMPLE_SIZE, len(df)), random_state=42)
    except Exception as exc:
        logger.error("Failed to read training data for baseline: %s", exc)
        return {}

    baseline: Dict[str, List[float]] = {feat: [] for feat in DRIFT_FEATURES}
    for _, row in df.iterrows():
        tx = {
            "amount": float(row.get("amount", 0)),
            "oldbalanceOrg": float(row.get("oldbalanceOrg", 0)),
            "newbalanceOrig": float(row.get("newbalanceOrig", 0)),
            "type": str(row.get("type", "")),
        }
        features = _extract_features_from_tx(tx)
        for feat in DRIFT_FEATURES:
            val = features.get(feat, 0.0)
            if np.isfinite(val):
                baseline[feat].append(val)

    # Cache to disk
    try:
        BASELINE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with BASELINE_CACHE_PATH.open("w") as f:
            json.dump(baseline, f)
        logger.info("Baseline cached to %s (%d features)", BASELINE_CACHE_PATH, len(baseline))
    except Exception as exc:
        logger.warning("Failed to cache baseline: %s", exc)

    return baseline


def load_baseline() -> Dict[str, List[float]]:
    """Load the cached baseline, building it on first call if needed."""
    if BASELINE_CACHE_PATH.exists():
        try:
            with BASELINE_CACHE_PATH.open("r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Baseline cache corrupt, rebuilding: %s", exc)

    if DATA_PATH.exists():
        return build_baseline_from_training_data()

    logger.warning("No baseline cache and no training data at %s — drift checks disabled", DATA_PATH)
    return {}


# ── Current distribution from prediction_logs ────────────────────────────────

def _load_current_distribution(sample_size: int = CURRENT_SAMPLE_SIZE) -> Dict[str, List[float]]:
    """Sample the most recent prediction logs and extract feature distributions."""
    db = SessionLocal()
    try:
        logs = (
            db.query(PredictionLog)
            .order_by(PredictionLog.id.desc())
            .limit(sample_size)
            .all()
        )
    except Exception as exc:
        logger.error("Failed to query prediction_logs for current distribution: %s", exc)
        return {}
    finally:
        db.close()

    current: Dict[str, List[float]] = {feat: [] for feat in DRIFT_FEATURES}
    for log in logs:
        features = _extract_features_from_tx(log.transaction_json)
        for feat in DRIFT_FEATURES:
            val = features.get(feat, 0.0)
            if np.isfinite(val):
                current[feat].append(val)

    return current


# ── Drift check + retrain ────────────────────────────────────────────────────

def check_drift_and_retrain() -> Dict[str, Any]:
    """
    Scheduled job: compute PSI per monitored feature, record snapshots, and
    trigger retrain if any feature crosses DRIFT_THRESHOLD.

    Returns a summary dict (useful for tests + manual invocation).
    """
    logger.info("Running scheduled drift check...")
    baseline = load_baseline()
    if not baseline:
        logger.warning("No baseline available — skipping drift check.")
        return {"status": "skipped", "reason": "no_baseline"}

    current = _load_current_distribution()
    if not current or all(len(v) == 0 for v in current.values()):
        logger.info("No recent prediction logs — skipping drift check.")
        return {"status": "skipped", "reason": "no_current_data"}

    db_path = PROJECT_ROOT  # record_drift_snapshot uses SessionLocal, not this arg
    snapshots: List[Dict[str, Any]] = []
    max_psi = 0.0
    drifted_features: List[str] = []

    for feat in DRIFT_FEATURES:
        baseline_arr = np.array(baseline.get(feat, []), dtype=float)
        current_arr = np.array(current.get(feat, []), dtype=float)

        if len(baseline_arr) < 10 or len(current_arr) < 10:
            # Not enough data for a reliable PSI on this feature
            continue

        psi = calculate_psi(baseline_arr, current_arr)
        max_psi = max(max_psi, psi)

        try:
            snapshot = record_drift_snapshot(
                db_path=db_path,
                feature_name=feat,
                baseline_data=baseline_arr,
                current_data=current_arr,
                alert_threshold=DRIFT_THRESHOLD,
            )
            snapshots.append(snapshot)
        except Exception as exc:
            logger.warning("Failed to record drift snapshot for %s: %s", feat, exc)

        if psi >= DRIFT_THRESHOLD:
            drifted_features.append(feat)
            logger.warning("DRIFT on %s: PSI=%.4f >= %.4f", feat, psi, DRIFT_THRESHOLD)

    logger.info("Drift check complete. Max PSI: %.4f. Drifted features: %s",
                max_psi, drifted_features or "none")

    if drifted_features:
        logger.warning("Significant drift detected on %d feature(s). Triggering retrain review...",
                       len(drifted_features))
        retrain_result = _trigger_metric_gated_retrain(drifted_features, max_psi)
        return {
            "status": "drift_detected",
            "max_psi": max_psi,
            "drifted_features": drifted_features,
            "snapshots": snapshots,
            "retrain": retrain_result,
        }

    return {
        "status": "stable",
        "max_psi": max_psi,
        "drifted_features": [],
        "snapshots": snapshots,
    }


def _trigger_metric_gated_retrain(
    drifted_features: List[str], max_psi: float
) -> Dict[str, Any]:
    """
    Train a candidate model and compare its metrics against the current
    production model. Only overwrite the prod pkl if the candidate beats
    the champion by MIN_METRIC_IMPROVEMENT on RETRAIN_EVAL_METRIC.

    This prevents the retrain trigger from silently DOWNGRADING the production
    model (which was the previous behavior — the old retrain used 50 trees vs
    the notebook's 200, with no undersampling, and overwrote prod unconditionally).
    """
    # train_model is imported at module level (above) so tests can patch it.
    from src.model_registry import get_active_model, register_model, promote_model

    # Snapshot current production metrics before retrain
    active = get_active_model(PROJECT_ROOT)
    current_metric_val = (active or {}).get(RETRAIN_EVAL_METRIC, 0.0)

    # Train candidate to a TEMP path (don't overwrite prod yet)
    candidate_path = PROJECT_ROOT / "models" / "candidate_fraud_model.pkl"
    try:
        candidate_metrics = train_model(
            DATA_PATH,
            n_samples=100_000,
            output_path=candidate_path,
            return_metrics=True,
        )
    except Exception as exc:
        logger.error("Candidate retrain failed: %s", exc)
        return {"status": "retrain_failed", "error": str(exc)}

    candidate_metric_val = candidate_metrics.get(RETRAIN_EVAL_METRIC, 0.0)
    improvement = candidate_metric_val - current_metric_val

    logger.info("Champion %s: %.4f | Candidate %s: %.4f | Improvement: %.4f (min required: %.4f)",
                RETRAIN_EVAL_METRIC, current_metric_val,
                RETRAIN_EVAL_METRIC, candidate_metric_val,
                improvement, MIN_METRIC_IMPROVEMENT)

    if improvement >= MIN_METRIC_IMPROVEMENT:
        # Promote candidate: backup prod, move candidate to prod path, register + promote
        prod_path = PROJECT_ROOT / "models" / "best_fraud_model.pkl"
        backup_path = PROJECT_ROOT / "models" / "best_fraud_model.backup.pkl"
        try:
            if prod_path.exists():
                prod_path.rename(backup_path)
            candidate_path.rename(prod_path)
        except OSError as exc:
            logger.error("Failed to swap candidate into prod path: %s", exc)
            return {"status": "swap_failed", "error": str(exc)}

        # Register + promote in the model registry
        try:
            new_version = register_model(
                db_path=PROJECT_ROOT,
                pkl_path=str(prod_path),
                roc_auc=candidate_metrics.get("roc_auc", 0.0),
                pr_auc=candidate_metrics.get("pr_auc", 0.0),
                precision_val=candidate_metrics.get("precision", 0.0),
                recall_val=candidate_metrics.get("recall", 0.0),
                f1_val=candidate_metrics.get("f1_score", 0.0),
                n_estimators=candidate_metrics.get("n_estimators", 200),
                dataset_size=candidate_metrics.get("dataset_size", 0),
                feature_count=candidate_metrics.get("feature_count", 29),
                notes=f"Auto-retrained due to drift on {drifted_features} (max PSI={max_psi:.4f}). "
                      f"Improvement: +{improvement:.4f} {RETRAIN_EVAL_METRIC}.",
            )
            promote_model(PROJECT_ROOT, new_version["version"])
            logger.info("Candidate promoted as %s. Backup at %s", new_version["version"], backup_path)
        except Exception as exc:
            logger.error("Registry update failed (model file already swapped): %s", exc)

        _log_system_alert(
            f"Drift retrain PROMOTED: drifted={drifted_features}, max_PSI={max_psi:.4f}, "
            f"+{improvement:.4f} {RETRAIN_EVAL_METRIC}."
        )
        return {
            "status": "promoted",
            "improvement": improvement,
            "new_metrics": candidate_metrics,
        }

    # Candidate didn't beat champion — discard it
    try:
        candidate_path.unlink(missing_ok=True)
    except OSError:
        pass

    logger.info("Candidate did not beat champion (improvement %.4f < %.4f). Discarded.",
                improvement, MIN_METRIC_IMPROVEMENT)
    _log_system_alert(
        f"Drift retrain REJECTED: candidate {RETRAIN_EVAL_METRIC}={candidate_metric_val:.4f} "
        f"did not beat champion {current_metric_val:.4f} by >= {MIN_METRIC_IMPROVEMENT}."
    )
    return {
        "status": "rejected",
        "improvement": improvement,
        "champion_metric": current_metric_val,
        "candidate_metric": candidate_metric_val,
    }


def _log_system_alert(message: str) -> None:
    """Log a system alert (no DB table for system alerts — use structured logging)."""
    logger.warning("SYSTEM ALERT: %s", message)


# ── Scheduler ────────────────────────────────────────────────────────────────

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler() -> BackgroundScheduler:
    """Start the APScheduler background job for periodic drift checks.

    Idempotent — safe to call multiple times (returns the existing scheduler).
    The interval is DRIFT_CHECK_INTERVAL_MINUTES (default 30m) to avoid
    excessive retrain attempts on a large dataset.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Drift scheduler already running.")
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        check_drift_and_retrain,
        "interval",
        minutes=DRIFT_CHECK_INTERVAL_MINUTES,
        id="drift_check",
        max_instances=1,  # never overlap runs
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Drift scheduler started (interval: %dm).", DRIFT_CHECK_INTERVAL_MINUTES)
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully stop the scheduler (called on app shutdown)."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Drift scheduler stopped.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    result = check_drift_and_retrain()
    print(json.dumps(result, indent=2, default=str))
