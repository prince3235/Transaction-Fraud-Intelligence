"""
Enterprise Data Drift Monitor.

Provides:
- Population Stability Index (PSI) calculation for numerical features
- Drift snapshot logging to database
- Threshold alerting
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.db import SessionLocal
from src.models import DriftSnapshot


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """
    Calculate the Population Stability Index (PSI) between two arrays.
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Create quantile bins based on the expected distribution
    bins = np.percentile(expected, np.linspace(0, 100, buckets + 1))
    bins[0] = -np.inf
    bins[-1] = np.inf

    # Count occurrences in bins
    expected_percents = np.histogram(expected, bins=bins)[0] / len(expected)
    actual_percents = np.histogram(actual, bins=bins)[0] / len(actual)

    # Avoid zero division
    expected_percents = np.clip(expected_percents, 0.0001, 1.0)
    actual_percents = np.clip(actual_percents, 0.0001, 1.0)

    psi = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
    return float(psi)


def record_drift_snapshot(
    db_path: Path,
    feature_name: str,
    baseline_data: np.ndarray,
    current_data: np.ndarray,
    alert_threshold: float = 0.2,
) -> Dict[str, Any]:
    """
    Calculate PSI for a feature and save the snapshot to the database.
    """
    psi_score = calculate_psi(baseline_data, current_data)
    alert = 1 if psi_score >= alert_threshold else 0
    
    baseline_mean = float(np.mean(baseline_data)) if len(baseline_data) > 0 else 0.0
    current_mean = float(np.mean(current_data)) if len(current_data) > 0 else 0.0
    
    baseline_std = float(np.std(baseline_data)) if len(baseline_data) > 0 else 0.0
    current_std = float(np.std(current_data)) if len(current_data) > 0 else 0.0
    
    now = _now()
    today = now[:10]
    
    db = SessionLocal()
    try:
        snapshot = DriftSnapshot(
            snapshot_date=today,
            feature_name=feature_name,
            psi_score=psi_score,
            alert_triggered=bool(alert),
            baseline_mean=baseline_mean,
            current_mean=current_mean,
            baseline_std=baseline_std,
            current_std=current_std,
            created_at=now
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        return {
            "id": snapshot.id,
            "snapshot_date": snapshot.snapshot_date,
            "feature_name": snapshot.feature_name,
            "psi_score": snapshot.psi_score,
            "alert_triggered": snapshot.alert_triggered,
            "baseline_mean": snapshot.baseline_mean,
            "current_mean": snapshot.current_mean,
            "baseline_std": snapshot.baseline_std,
            "current_std": snapshot.current_std,
            "created_at": snapshot.created_at
        }
    finally:
        db.close()


def get_latest_drift_snapshots(db_path: Path) -> List[Dict[str, Any]]:
    """Get the most recent snapshot for each feature."""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        # Find latest ID per feature_name
        subq = db.query(
            func.max(DriftSnapshot.id).label('max_id')
        ).group_by(DriftSnapshot.feature_name).subquery()
        
        snapshots = db.query(DriftSnapshot).join(
            subq, DriftSnapshot.id == subq.c.max_id
        ).order_by(DriftSnapshot.psi_score.desc()).all()
        
        return [{
            "id": s.id,
            "snapshot_date": s.snapshot_date,
            "feature_name": s.feature_name,
            "psi_score": s.psi_score,
            "alert_triggered": s.alert_triggered,
            "baseline_mean": s.baseline_mean,
            "current_mean": s.current_mean,
            "baseline_std": s.baseline_std,
            "current_std": s.current_std,
            "created_at": s.created_at
        } for s in snapshots]
    finally:
        db.close()
