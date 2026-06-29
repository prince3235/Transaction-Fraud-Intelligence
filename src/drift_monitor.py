"""
Enterprise Data Drift Monitor.

Provides:
- Population Stability Index (PSI) calculation for numerical features
- Drift snapshot logging to database
- Threshold alerting
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """
    Calculate the Population Stability Index (PSI) between two arrays.
    
    Args:
        expected: Baseline/Training distribution array.
        actual: Current/Production distribution array.
        buckets: Number of quantiles to use for binning.
        
    Returns:
        float PSI score.
        < 0.1: No significant change
        0.1 - 0.2: Moderate change
        > 0.2: Significant change (drift detected)
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
    
    con = _connect(db_path)
    cur = con.cursor()
    
    cur.execute(
        """
        INSERT INTO drift_snapshots 
            (snapshot_date, feature_name, psi_score, alert_triggered, 
             baseline_mean, current_mean, baseline_std, current_std, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (today, feature_name, psi_score, alert, baseline_mean, current_mean, baseline_std, current_std, now)
    )
    con.commit()
    row_id = cur.lastrowid
    
    cur.execute("SELECT * FROM drift_snapshots WHERE id = ?", (row_id,))
    row = cur.fetchone()
    con.close()
    return dict(row)


def get_latest_drift_snapshots(db_path: Path) -> List[Dict[str, Any]]:
    """Get the most recent snapshot for each feature."""
    query = """
        SELECT * FROM drift_snapshots
        WHERE id IN (
            SELECT MAX(id) FROM drift_snapshots GROUP BY feature_name
        )
        ORDER BY psi_score DESC
    """
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]
