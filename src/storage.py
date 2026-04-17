from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_db_path(base_dir: Path) -> Path:
    # keep DB inside data/ so it is clearly separate
    db_dir = base_dir / "data" / "app_db"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "fraud_intelligence.db"


def connect(db_path: Path) -> sqlite3.Connection:
    # check_same_thread False helps when server uses threads
    return sqlite3.connect(db_path, check_same_thread=False)


def init_db(db_path: Path) -> None:
    con = connect(db_path)
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            transaction_json TEXT NOT NULL,
            ml_probability REAL NOT NULL,
            ml_risk_level TEXT NOT NULL,
            ml_risk_score INTEGER NOT NULL,
            final_risk_level TEXT NOT NULL,
            final_risk_score INTEGER NOT NULL,
            policy_override_applied INTEGER NOT NULL,
            policy_reasons_json TEXT NOT NULL,
            suspicious_signal_count INTEGER,
            alert_json TEXT
        )
        """
    )

    con.commit()
    con.close()


def log_prediction(
    db_path: Path,
    created_at: str,
    transaction: Dict[str, Any],
    ml_probability: float,
    ml_risk_level: str,
    ml_risk_score: int,
    final_risk_level: str,
    final_risk_score: int,
    policy_override_applied: bool,
    policy_reasons: List[str],
    suspicious_signal_count: Optional[int] = None,
    alert: Optional[Dict[str, Any]] = None,
) -> None:
    con = connect(db_path)
    cur = con.cursor()

    cur.execute(
        """
        INSERT INTO prediction_logs (
            created_at, transaction_json,
            ml_probability, ml_risk_level, ml_risk_score,
            final_risk_level, final_risk_score,
            policy_override_applied, policy_reasons_json,
            suspicious_signal_count, alert_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            created_at,
            json.dumps(transaction),
            float(ml_probability),
            str(ml_risk_level),
            int(ml_risk_score),
            str(final_risk_level),
            int(final_risk_score),
            1 if policy_override_applied else 0,
            json.dumps(policy_reasons),
            int(suspicious_signal_count) if suspicious_signal_count is not None else None,
            json.dumps(alert) if alert is not None else None,
        ),
    )

    con.commit()
    con.close()


def fetch_recent_logs(db_path: Path, limit: int = 50) -> List[Dict[str, Any]]:
    con = connect(db_path)
    cur = con.cursor()

    cur.execute(
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
        (int(limit),),
    )

    rows = cur.fetchall()
    con.close()

    out = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "created_at": r[1],
                "transaction": json.loads(r[2]),
                "ml_probability": r[3],
                "ml_risk_level": r[4],
                "ml_risk_score": r[5],
                "final_risk_level": r[6],
                "final_risk_score": r[7],
                "policy_override_applied": bool(r[8]),
                "policy_reasons": json.loads(r[9]),
                "suspicious_signal_count": r[10],
                "alert": json.loads(r[11]) if r[11] else None,
            }
        )
    return out