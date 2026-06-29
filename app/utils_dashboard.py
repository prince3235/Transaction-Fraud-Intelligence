import json
import sqlite3
from pathlib import Path

import pandas as pd


def get_db_path(project_root: Path) -> Path:
    """Return absolute path to the SQLite database."""
    return project_root / "data" / "app_db" / "fraud_intelligence.db"


def get_total_count(db_path: Path) -> int:
    """Return total number of prediction logs in the database."""
    if not db_path.exists():
        return 0
    try:
        con = sqlite3.connect(db_path, check_same_thread=False)
        count = con.execute("SELECT COUNT(*) FROM prediction_logs").fetchone()[0]
        return int(count)
    except Exception:
        return 0
    finally:
        con.close()


def _safe_json(value, fallback):
    """
    Safely parse a JSON column value.
    Handles: None, float NaN, empty string, malformed JSON.
    Returns fallback ({} or []) on any failure.
    """
    if value is None:
        return fallback
    if not isinstance(value, str):   # catches float NaN from SQLite NULL
        return fallback
    value = value.strip()
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return fallback


def load_logs_df(db_path: Path, limit: int | None = None) -> pd.DataFrame:
    """
    Load prediction logs from SQLite into a clean DataFrame.

    Args:
        db_path : Path to the SQLite database file.
        limit   : Max rows to fetch (None = all rows).

    Returns:
        pd.DataFrame with parsed JSON columns and typed dtypes.
        Empty DataFrame if DB missing or table empty.
    """
    if not db_path.exists():
        return pd.DataFrame()

    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    query = f"""
        SELECT
            id,
            created_at,
            transaction_json,
            ml_probability,
            ml_risk_level,
            ml_risk_score,
            final_risk_level,
            final_risk_score,
            policy_override_applied,
            policy_reasons_json,
            suspicious_signal_count,
            alert_json,
            status
        FROM prediction_logs
        ORDER BY id DESC
        {limit_clause}
    """

    try:
        con = sqlite3.connect(db_path, check_same_thread=False)
        df = pd.read_sql_query(query, con)
    except Exception:
        return pd.DataFrame()
    finally:
        con.close()

    if df.empty:
        return df

    # ── Datetime ────────────────────────────────────────────────────────────
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    # ── JSON columns — all use _safe_json so NaN never crashes ──────────────
    df["transaction"]    = df["transaction_json"].apply(lambda x: _safe_json(x, {}))
    df["policy_reasons"] = df["policy_reasons_json"].apply(lambda x: _safe_json(x, []))
    df["alert"]          = df["alert_json"].apply(lambda x: _safe_json(x, None))

    # ── Numeric types ────────────────────────────────────────────────────────
    df["ml_probability"]         = pd.to_numeric(df["ml_probability"],         errors="coerce").fillna(0.0)
    df["ml_risk_score"]          = pd.to_numeric(df["ml_risk_score"],           errors="coerce").fillna(0).astype(int)
    df["final_risk_score"]       = pd.to_numeric(df["final_risk_score"],        errors="coerce").fillna(0).astype(int)
    df["suspicious_signal_count"]= pd.to_numeric(df["suspicious_signal_count"], errors="coerce").fillna(0).astype(int)
    df["policy_override_applied"]= pd.to_numeric(df["policy_override_applied"], errors="coerce").fillna(0).astype(int)

    return df