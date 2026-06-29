"""
Enterprise Model Registry.

Provides:
- Version tracking for trained models
- Metadata and metrics serialization
- Model promotion (active/production flag)
- Archiving and rollback support
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def list_model_versions(db_path: Path, include_archived: bool = False) -> List[Dict[str, Any]]:
    """Return all model versions in descending order of creation."""
    query = "SELECT * FROM model_registry"
    if not include_archived:
        query += " WHERE is_archived = 0"
    query += " ORDER BY id DESC"
    
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_active_model(db_path: Path) -> Optional[Dict[str, Any]]:
    """Return the currently active production model."""
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT * FROM model_registry WHERE is_production = 1 LIMIT 1")
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None


def register_model(
    db_path: Path,
    pkl_path: str,
    roc_auc: float,
    pr_auc: float,
    precision_val: float,
    recall_val: float,
    f1_val: float,
    n_estimators: int,
    dataset_size: int,
    feature_count: int,
    notes: str = "",
) -> Dict[str, Any]:
    """Register a newly trained model version."""
    con = _connect(db_path)
    cur = con.cursor()
    
    cur.execute("SELECT COUNT(*) FROM model_registry")
    count = cur.fetchone()[0]
    version = f"v{count + 1}"
    
    # Newly registered model is not automatically production
    now = _now()
    cur.execute(
        """
        INSERT INTO model_registry
            (version, pkl_path, roc_auc, pr_auc, precision_val, recall_val, f1_val,
             n_estimators, training_date, dataset_size, feature_count, notes,
             is_production, is_archived, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
        """,
        (
            version, pkl_path, roc_auc, pr_auc, precision_val, recall_val, f1_val,
            n_estimators, now[:10], dataset_size, feature_count, notes, now
        )
    )
    con.commit()
    row_id = cur.lastrowid
    
    cur.execute("SELECT * FROM model_registry WHERE id = ?", (row_id,))
    row = cur.fetchone()
    con.close()
    return dict(row)


def promote_model(db_path: Path, version: str) -> None:
    """Set the given version as the active production model."""
    con = _connect(db_path)
    cur = con.cursor()
    
    # Demote all current models
    cur.execute("UPDATE model_registry SET is_production = 0")
    # Promote the target model
    cur.execute("UPDATE model_registry SET is_production = 1 WHERE version = ?", (version,))
    
    con.commit()
    con.close()


def archive_model(db_path: Path, version: str) -> None:
    """Archive a model (cannot archive the active production model)."""
    con = _connect(db_path)
    cur = con.cursor()
    
    cur.execute("SELECT is_production FROM model_registry WHERE version = ?", (version,))
    row = cur.fetchone()
    if row and row["is_production"] == 1:
        con.close()
        raise ValueError("Cannot archive the active production model.")
        
    cur.execute("UPDATE model_registry SET is_archived = 1 WHERE version = ?", (version,))
    con.commit()
    con.close()
