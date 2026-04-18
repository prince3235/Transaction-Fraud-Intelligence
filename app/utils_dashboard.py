import json
import sqlite3
from pathlib import Path

import pandas as pd


def get_db_path(project_root: Path) -> Path:
    return project_root / "data" / "app_db" / "fraud_intelligence.db"


def load_logs_df(db_path: Path, limit: int = 5000) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()

    con = sqlite3.connect(db_path, check_same_thread=False)
    df = pd.read_sql_query(
        """
        SELECT id, created_at, transaction_json,
               ml_probability, ml_risk_level, ml_risk_score,
               final_risk_level, final_risk_score,
               policy_override_applied, policy_reasons_json,
               suspicious_signal_count, alert_json
        FROM prediction_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        con,
        params=(int(limit),),
    )
    con.close()

    if df.empty:
        return df

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["transaction"] = df["transaction_json"].apply(lambda x: json.loads(x) if x else {})
    df["policy_reasons"] = df["policy_reasons_json"].apply(lambda x: json.loads(x) if x else [])
    df["alert"] = df["alert_json"].apply(lambda x: json.loads(x) if x else None)

    return df