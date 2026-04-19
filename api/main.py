from datetime import timedelta
import random

from pathlib import Path
from datetime import datetime, timezone

import joblib
from fastapi import FastAPI
from pydantic import BaseModel, Field

import sqlite3
from datetime import datetime, timezone

from src.features import build_features, align_to_model_columns, load_json
from src.risk_scoring import score_probability, apply_policy_overrides
from src.alerts import create_alert, should_alert
from src.storage import get_db_path, init_db, log_prediction, fetch_recent_logs

app = FastAPI(title="Transaction Fraud Intelligence API", version="1.1.0")

BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = BASE_DIR / "models" / "best_fraud_model.pkl"
CONFIG_PATH = BASE_DIR / "models" / "feature_config.json"
COLS_PATH = BASE_DIR / "models" / "feature_columns.json"

model = joblib.load(MODEL_PATH)
config = load_json(CONFIG_PATH)
model_columns = load_json(COLS_PATH)

DB_PATH = get_db_path(BASE_DIR)
init_db(DB_PATH)


class TransactionIn(BaseModel):
    step: int = Field(..., ge=0)
    type: str
    amount: float = Field(..., ge=0)
    oldbalanceOrg: float = Field(..., ge=0)
    newbalanceOrig: float = Field(..., ge=0)
    oldbalanceDest: float = Field(..., ge=0)
    newbalanceDest: float = Field(..., ge=0)


@app.get("/health")
def health():
    return {"status": "ok", "db_path": str(DB_PATH)}


def score_tx(tx_dict: dict):
    # Build + align features
    X = build_features(tx_dict, config)
    X = align_to_model_columns(X, model_columns)

    # ML probability
    ml_prob = float(model.predict_proba(X)[:, 1][0])
    base_risk = score_probability(ml_prob)

    # Policy override
    features_dict = X.iloc[0].to_dict()
    policy_out = apply_policy_overrides(base_risk, features_dict)

    if isinstance(policy_out, tuple):
        final_risk, policy_reasons = policy_out
    else:
        final_risk, policy_reasons = policy_out, []

    # Alert (MEDIUM+)
    alert = None
    if should_alert(final_risk.risk_level, min_level="MEDIUM"):
        alert_obj = create_alert(
            transaction_ref="api_input",
            probability=final_risk.probability,
            risk_score=final_risk.risk_score,
            risk_level=final_risk.risk_level,
            recommended_action=final_risk.recommended_action,
            reasons=[{"reason": r} for r in policy_reasons],
        )
        alert = alert_obj.__dict__

    # for debugging
    suspicious_signal_count = int(features_dict.get("suspicious_signal_count", 0))

    return X, ml_prob, base_risk, final_risk, policy_reasons, alert, suspicious_signal_count


@app.post("/predict")
def predict(tx: TransactionIn):
    tx_dict = tx.model_dump()
    X, ml_prob, base_risk, final_risk, policy_reasons, alert, ssc = score_tx(tx_dict)

    created_at = datetime.now(timezone.utc).isoformat()

    # Log to SQLite
    log_prediction(
        db_path=DB_PATH,
        created_at=created_at,
        transaction=tx_dict,
        ml_probability=ml_prob,
        ml_risk_level=base_risk.risk_level,
        ml_risk_score=base_risk.risk_score,
        final_risk_level=final_risk.risk_level,
        final_risk_score=final_risk.risk_score,
        policy_override_applied=(final_risk.risk_level != base_risk.risk_level),
        policy_reasons=policy_reasons,
        suspicious_signal_count=ssc,
        alert=alert,
    )

    return {
        "ml_probability": ml_prob,  # no rounding
        "ml_risk_score": base_risk.risk_score,
        "ml_risk_level": base_risk.risk_level,
        "final_risk_score": final_risk.risk_score,
        "final_risk_level": final_risk.risk_level,
        "recommended_action": final_risk.recommended_action,
        "policy_override_applied": (final_risk.risk_level != base_risk.risk_level),
        "policy_reasons": policy_reasons,
        "alert": alert,
    }


@app.post("/debug/predict")
def debug_predict(tx: TransactionIn):
    tx_dict = tx.model_dump()
    X, ml_prob, base_risk, final_risk, policy_reasons, alert, ssc = score_tx(tx_dict)

    # Only show selected important engineered features (not full row)
    cols_to_show = [
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "log_amount",
        "amount_to_oldbalance_orig_ratio",
        "sender_account_emptied",
        "dest_received_large_amount",
        "is_large_transaction",
        "balance_error_orig",
        "balance_error_dest",
        "transactions_in_step",
        "is_high_velocity_step",
        "type_encoded",
        "type_risk_score",
        "suspicious_signal_count",
    ]
    debug_features = {c: float(X.iloc[0][c]) if c in X.columns else None for c in cols_to_show}

    return {
        "input_transaction": tx_dict,
        "debug_features": debug_features,
        "ml_probability": ml_prob,
        "ml_risk_level": base_risk.risk_level,
        "ml_risk_score": base_risk.risk_score,
        "final_risk_level": final_risk.risk_level,
        "final_risk_score": final_risk.risk_score,
        "policy_override_applied": (final_risk.risk_level != base_risk.risk_level),
        "policy_reasons": policy_reasons,
        "alert": alert,
    }


@app.get("/logs/recent")
def recent_logs(limit: int = 50):
    return {"limit": limit, "items": fetch_recent_logs(DB_PATH, limit=limit)}

@app.post("/admin/seed-logs")
def seed_logs(count: int = 500):
    import pandas as pd
    import json

    X_TEST_PATH = BASE_DIR / "data" / "processed" / "X_test.csv"
    X_test = pd.read_csv(X_TEST_PATH)

    sample_df = X_test.sample(n=min(count, len(X_test)), random_state=42)
    sample_df = sample_df[model_columns]

    ml_probs = model.predict_proba(sample_df)[:, 1]
    created_at = datetime.now(timezone.utc).isoformat()

    rows = []
    for i, (_, row) in enumerate(sample_df.iterrows()):
        ml_prob = float(ml_probs[i])
        base_risk = score_probability(ml_prob)

        features_dict = row.to_dict()
        policy_out = apply_policy_overrides(base_risk, features_dict)

        if isinstance(policy_out, tuple):
            final_risk, policy_reasons = policy_out
        else:
            final_risk, policy_reasons = policy_out, []

        alert = None
        if should_alert(final_risk.risk_level, min_level="MEDIUM"):
            alert_obj = create_alert(
                transaction_ref=f"seed_{i}",
                probability=final_risk.probability,
                risk_score=final_risk.risk_score,
                risk_level=final_risk.risk_level,
                recommended_action=final_risk.recommended_action,
                reasons=[{"reason": r} for r in policy_reasons],
            )
            alert = alert_obj.__dict__

        tx = {k: float(v) if isinstance(v, (float, int)) else str(v) for k, v in features_dict.items() if k in ["step","amount","oldbalanceOrg","newbalanceOrig","oldbalanceDest","newbalanceDest"]}

        rows.append((
            created_at, json.dumps(tx),
            float(ml_prob), str(base_risk.risk_level), int(base_risk.risk_score),
            str(final_risk.risk_level), int(final_risk.risk_score),
            1 if (final_risk.risk_level != base_risk.risk_level) else 0,
            json.dumps(policy_reasons),
            int(features_dict.get("suspicious_signal_count", 0)),
            json.dumps(alert) if alert else None
        ))

    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = con.cursor()
    cur.executemany(
        """INSERT INTO prediction_logs (
            created_at, transaction_json,
            ml_probability, ml_risk_level, ml_risk_score,
            final_risk_level, final_risk_score,
            policy_override_applied, policy_reasons_json,
            suspicious_signal_count, alert_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows
    )
    con.commit()
    con.close()

    return {"status": "ok", "inserted": len(rows)}    

@app.post("/admin/seed-logs")
def seed_logs(count: int = 1000):
    import pandas as pd
    import json
    import sqlite3
    from datetime import datetime, timezone

    X_TEST_PATH = BASE_DIR / "data" / "processed" / "X_test.csv"
    X_test = pd.read_csv(X_TEST_PATH)

    sample_df = X_test.sample(n=min(count, len(X_test)), random_state=42)
    sample_df = sample_df[model_columns]

    ml_probs = model.predict_proba(sample_df)[:, 1]
    
    import random
    from datetime import timedelta
    offset_minutes = random.randint(0, 60*24*7)
    created_at = (datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)).isoformat()

    rows = []
    for i, (_, row) in enumerate(sample_df.iterrows()):
        ml_prob = float(ml_probs[i])
        base_risk = score_probability(ml_prob)

        features_dict = row.to_dict()
        policy_out = apply_policy_overrides(base_risk, features_dict)

        if isinstance(policy_out, tuple):
            final_risk, policy_reasons = policy_out
        else:
            final_risk, policy_reasons = policy_out, []

        alert = None
        if should_alert(final_risk.risk_level, min_level="MEDIUM"):
            alert_obj = create_alert(
                transaction_ref=f"seed_{i}",
                probability=final_risk.probability,
                risk_score=final_risk.risk_score,
                risk_level=final_risk.risk_level,
                recommended_action=final_risk.recommended_action,
                reasons=[{"reason": r} for r in policy_reasons],
            )
            alert = alert_obj.__dict__

        tx = {k: float(v) if isinstance(v, (float, int)) else str(v) for k, v in features_dict.items() if k in ["step","amount","oldbalanceOrg","newbalanceOrig","oldbalanceDest","newbalanceDest"]}

        rows.append((
            created_at, json.dumps(tx),
            float(ml_prob), str(base_risk.risk_level), int(base_risk.risk_score),
            str(final_risk.risk_level), int(final_risk.risk_score),
            1 if (final_risk.risk_level != base_risk.risk_level) else 0,
            json.dumps(policy_reasons),
            int(features_dict.get("suspicious_signal_count", 0)),
            json.dumps(alert) if alert else None
        ))

    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = con.cursor()
    cur.executemany(
        """INSERT INTO prediction_logs (
            created_at, transaction_json,
            ml_probability, ml_risk_level, ml_risk_score,
            final_risk_level, final_risk_score,
            policy_override_applied, policy_reasons_json,
            suspicious_signal_count, alert_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows
    )
    con.commit()
    con.close()

    return {"status": "ok", "inserted": len(rows)}    


# ========== ADMIN & MONITORING ENDPOINTS ==========

@app.get("/stats")
def get_stats():
    """Get system-level statistics for monitoring"""
    import sqlite3
    import pandas as pd
    
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    
    total = con.execute("SELECT COUNT(*) FROM prediction_logs").fetchone()[0]
    
    risk_dist = pd.read_sql_query(
        "SELECT final_risk_level, COUNT(*) as count FROM prediction_logs GROUP BY final_risk_level",
        con
    ).to_dict(orient="records")
    
    override_rate = con.execute(
        "SELECT AVG(policy_override_applied)*100 FROM prediction_logs"
    ).fetchone()[0]
    
    avg_score = con.execute(
        "SELECT AVG(final_risk_score) FROM prediction_logs"
    ).fetchone()[0]
    
    con.close()
    
    return {
        "total_scored": total,
        "risk_distribution": risk_dist,
        "override_rate_pct": round(override_rate, 2) if override_rate else 0,
        "avg_risk_score": round(avg_score, 2) if avg_score else 0
    }


@app.get("/logs/{log_id}/explain")
def explain_log(log_id: int):
    """Get detailed explanation for a specific log entry"""
    import sqlite3
    import json
    
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = con.cursor()
    
    row = cur.execute(
        """SELECT transaction_json, ml_probability, ml_risk_level, ml_risk_score,
                  final_risk_level, final_risk_score, policy_override_applied, policy_reasons_json
           FROM prediction_logs WHERE id = ?""",
        (int(log_id),)
    ).fetchone()
    
    con.close()
    
    if not row:
        return {"error": "log not found"}
    
    return {
        "log_id": log_id,
        "transaction": json.loads(row[0]),
        "ml": {
            "probability": row[1],
            "level": row[2],
            "score": row[3]
        },
        "final": {
            "level": row[4],
            "score": row[5]
        },
        "override_applied": bool(row[6]),
        "override_reasons": json.loads(row[7]) if row[7] else [],
        "explanation": "ML model assessed base risk. Policy engine may have elevated it based on business rules."
    }    