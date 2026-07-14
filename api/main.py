from datetime import timedelta
import random
import logging
import os
from typing import Optional

from pathlib import Path
from datetime import datetime, timezone

import joblib
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from src.features import build_features, align_to_model_columns, load_json
from src.risk_scoring import score_probability, apply_policy_overrides
from src.alerts import create_alert, should_alert
from src.storage import get_db_path, init_db, log_prediction, fetch_recent_logs
from src.auth import authenticate, has_permission
from src.rules_engine import evaluate_rules

# Default Anthropic model — env-overridable. claude-sonnet-4-6 is NOT a real
# model ID; we use the env var or fall back to a valid public ID.
ANTHROPIC_MODEL_NAME = os.environ.get(
    "ANTHROPIC_MODEL", "claude-sonnet-4-5"
)

app = FastAPI(title="Transaction Fraud Intelligence API", version="1.1.0")

# ── CORS middleware ─────────────────────────────────────────────────────────
# Allow the configured frontend origins (comma-separated in CORS_ORIGINS).
# Default permits localhost Streamlit + Next.js dev servers.
_DEFAULT_ORIGINS = (
    "http://localhost:8501,http://127.0.0.1:8501,"
    "http://localhost:3000,http://127.0.0.1:3000"
)
_allowed_origins = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth (Bearer token → user dict) ─────────────────────────────────────────
_security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> dict:
    """
    Resolve the bearer token to a user dict.

    The token is interpreted as a session token issued by `/auth/login`.
    In this simplified implementation we accept the API_AUTH_TOKEN env var
    (constant-time compared) and return the admin user. Real deployments should
    swap this for a session-token table lookup (see src/auth.generate_session_token).
    """
    # Public endpoints bypass this via `dependencies=[]`; protected ones require it.
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials

    # If a static admin API token is configured, accept it (constant-time).
    api_token = os.environ.get("API_AUTH_TOKEN", "")
    if api_token:
        import hmac
        if hmac.compare_digest(token, api_token):
            return {"id": 0, "username": "api-client", "role": "Admin"}

    # Otherwise treat token as username:password (demo convenience, never for prod)
    # — this lets the Streamlit UI log in with the demo credentials.
    if ":" in token:
        username, password = token.split(":", 1)
        user = authenticate(DB_PATH, username, password)
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: str):
    """FastAPI dependency factory that enforces a specific RBAC permission."""
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if not has_permission(user.get("role", ""), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role `{user.get('role')}` lacks permission `{permission}`",
            )
        return user
    return _checker

BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = BASE_DIR / "models" / "best_fraud_model.pkl"
CONFIG_PATH = BASE_DIR / "models" / "feature_config.json"
COLS_PATH = BASE_DIR / "models" / "feature_columns.json"


def _load_model_from_registry():
    """
    Load the model pkl, consulting the model registry for the active version's
    pkl_path. Falls back to the default MODEL_PATH if the registry is empty
    or the registered path doesn't exist on disk.
    """
    try:
        from src.model_registry import get_active_model
        active = get_active_model(BASE_DIR)
        if active and active.get("pkl_path"):
            registered_path = Path(active["pkl_path"])
            if not registered_path.is_absolute():
                registered_path = BASE_DIR / registered_path
            if registered_path.exists():
                logger.info("Loading model %s from registry path: %s",
                            active.get("version"), registered_path)
                return joblib.load(registered_path), active
    except Exception as exc:
        logger.warning("Model registry lookup failed, falling back to default path: %s", exc)

    logger.info("Loading model from default path: %s", MODEL_PATH)
    return joblib.load(MODEL_PATH), None


model, active_model_info = _load_model_from_registry()
config = load_json(CONFIG_PATH)
model_columns = load_json(COLS_PATH)

DB_PATH = get_db_path(BASE_DIR)
init_db(DB_PATH)


# ── Startup: start drift scheduler ───────────────────────────────────────────
@app.on_event("startup")
def _start_background_jobs():
    """Start the drift-monitor scheduler on app startup (was previously dead code)."""
    try:
        from src.retrain_trigger import start_scheduler
        start_scheduler()
    except Exception as exc:
        logger.warning("Failed to start drift scheduler (non-fatal): %s", exc)


@app.on_event("shutdown")
def _stop_background_jobs():
    """Gracefully stop the scheduler on app shutdown."""
    try:
        from src.retrain_trigger import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


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
    return {
        "status": "ok",
        "db_path": str(DB_PATH),
        "model_version": (active_model_info or {}).get("version", "unknown"),
    }


@app.post("/admin/reload-model")
def reload_model(user: dict = Depends(require_permission("retrain_model"))):
    """
    Reload the model from disk + registry. Call this after promoting a new
    model version in the registry so the running API process picks it up
    without needing a full restart.
    """
    global model, active_model_info
    try:
        model, active_model_info = _load_model_from_registry()
        return {
            "status": "ok",
            "model_version": (active_model_info or {}).get("version", "unknown"),
            "pkl_path": (active_model_info or {}).get("pkl_path", str(MODEL_PATH)),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload model: {exc}",
        )


def score_tx(tx_dict: dict):
    # Build + align features
    X = build_features(tx_dict, config)
    X = align_to_model_columns(X, model_columns)

    # ML probability
    ml_prob = float(model.predict_proba(X)[:, 1][0])
    base_risk = score_probability(ml_prob)

    # Policy override (static heuristics)
    features_dict = X.iloc[0].to_dict()
    policy_out = apply_policy_overrides(base_risk, features_dict)

    if isinstance(policy_out, tuple):
        final_risk, policy_reasons = policy_out
    else:
        final_risk, policy_reasons = policy_out, []

    # ── Rules engine (DB-driven, dynamic) ──────────────────────────────────
    # Evaluate active business rules against the engineered features and merge
    # any matches into the policy_reasons + bump risk level if the rule says so.
    rule_hits = []
    try:
        rule_final_level, triggered_rules = evaluate_rules(
            DB_PATH, features_dict, current_risk_level=final_risk.risk_level
        )
        for hit in triggered_rules:
            rule_hits.append({
                "name": hit.get("name"),
                "condition": hit.get("condition_json"),
                "action": hit.get("action"),
                "risk_level_bump": hit.get("risk_level_bump"),
                "reason": f"Rule matched: {hit.get('name')} -> {hit.get('action')} to {hit.get('risk_level_bump')}",
            })
            policy_reasons.append(f"Rule matched: {hit.get('name')}")

        # If rules engine escalated the level beyond what policy overides set,
        # bump the final_risk to match (only escalates, never de-escalates).
        if rule_final_level and rule_final_level != final_risk.risk_level:
            from src.risk_scoring import LEVEL_MIN_SCORE, LEVEL_ORDER, RiskResult, recommended_action
            if LEVEL_ORDER.get(rule_final_level, 0) > LEVEL_ORDER.get(final_risk.risk_level, 0):
                new_score = max(final_risk.risk_score, LEVEL_MIN_SCORE[rule_final_level])
                final_risk = RiskResult(
                    probability=final_risk.probability,
                    risk_score=new_score,
                    risk_level=rule_final_level,
                    recommended_action=recommended_action(rule_final_level),
                )
    except Exception as exc:
        logger.warning("Rules engine evaluation failed (non-fatal): %s", exc)

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

    return X, ml_prob, base_risk, final_risk, policy_reasons, alert, suspicious_signal_count, rule_hits


@app.post("/predict")
def predict(tx: TransactionIn, user: dict = Depends(get_current_user)):
    tx_dict = tx.model_dump()
    X, ml_prob, base_risk, final_risk, policy_reasons, alert, ssc, rule_hits = score_tx(tx_dict)

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
        "rule_hits": rule_hits,
        "alert": alert,
    }


@app.post("/debug/predict")
def debug_predict(tx: TransactionIn, user: dict = Depends(get_current_user)):
    tx_dict = tx.model_dump()
    X, ml_prob, base_risk, final_risk, policy_reasons, alert, ssc, rule_hits = score_tx(tx_dict)

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
def recent_logs(limit: int = 50, user: dict = Depends(get_current_user)):
    return {"limit": limit, "items": fetch_recent_logs(DB_PATH, limit=limit)}


@app.post("/admin/seed-logs")
def seed_logs(count: int = 1000, user: dict = Depends(require_permission("manage_users"))):
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
            json.dumps(alert) if alert else None,
            "APPROVED" if final_risk.risk_level == "LOW" else "PENDING_REVIEW"
        ))

    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = con.cursor()
    cur.executemany(
        """INSERT INTO prediction_logs (
            created_at, transaction_json,
            ml_probability, ml_risk_level, ml_risk_score,
            final_risk_level, final_risk_score,
            policy_override_applied, policy_reasons_json,
            suspicious_signal_count, alert_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows
    )
    con.commit()
    con.close()

    return {"status": "ok", "inserted": len(rows)}    


class ActionIn(BaseModel):
    status: str

@app.post("/logs/{log_id}/action")
def log_action(log_id: int, action: ActionIn, user: dict = Depends(require_permission("manage_cases"))):
    if action.status not in ("APPROVED", "BLOCKED"):
        raise HTTPException(status_code=422, detail="Invalid status — must be APPROVED or BLOCKED")
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = con.cursor()
    cur.execute("UPDATE prediction_logs SET status = ? WHERE id = ?", (action.status, int(log_id)))
    con.commit()
    con.close()
    return {"status": "ok", "id": log_id, "new_status": action.status}

# ========== ADMIN & MONITORING ENDPOINTS ==========

@app.get("/stats")
def get_stats(user: dict = Depends(get_current_user)):
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
def explain_log(log_id: int, user: dict = Depends(get_current_user)):
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


# ========== LLM COPILOT ENDPOINTS ==========

class CopilotRequest(BaseModel):
    prediction_log_id: Optional[int] = None
    case_id: Optional[str] = None
    follow_up: Optional[str] = None

    class Config:
        # Allow either prediction_log_id OR case_id
        pass


@app.post("/copilot/explain")
def copilot_explain(req: CopilotRequest, user: dict = Depends(get_current_user)):
    """
    Generate a natural-language explanation for a flagged transaction.

    Accepts either { "prediction_log_id": int } or { "case_id": str }.
    Optionally include { "follow_up": "Has this user been flagged before?" }
    for follow-up questions.

    Returns plain-English explanation written for compliance analyst audience.
    Logs every query + response to copilot_logs for regulatory audit trail.
    Falls back gracefully if LLM API is unavailable (never blocks analyst workflow).
    """
    if not req.prediction_log_id and not req.case_id:
        return {"error": "Either prediction_log_id or case_id is required.", "explanation": None}

    try:
        from src.llm_copilot import CopilotEngine
        from src.db_migrations import run_migrations

        # Ensure copilot_logs table exists
        run_migrations(DB_PATH)

        engine = CopilotEngine(db_path=DB_PATH, project_root=BASE_DIR)
        result = engine.explain(
            prediction_log_id=req.prediction_log_id,
            case_id=req.case_id,
            follow_up_question=req.follow_up,
        )

        return {
            "prediction_log_id": req.prediction_log_id,
            "case_id": req.case_id,
            "explanation": result.get("explanation"),
            "is_cached": result.get("is_cached", False),
            "latency_ms": result.get("latency_ms", 0),
            "error": result.get("error"),
            "model": ANTHROPIC_MODEL_NAME,
        }

    except Exception as exc:
        # Graceful degradation: never let LLM issues block the analyst UI
        import traceback
        logger.error("Copilot endpoint error: %s\n%s", exc, traceback.format_exc())
        return {
            "prediction_log_id": req.prediction_log_id,
            "case_id": req.case_id,
            "explanation": None,
            "error": f"Copilot temporarily unavailable: {type(exc).__name__}",
            "is_cached": False,
            "latency_ms": 0,
        }


@app.get("/copilot/logs")
def get_copilot_logs(limit: int = 50, user: dict = Depends(require_permission("view_audit"))):
    """Fetch recent copilot query audit logs (admin/compliance use)."""
    try:
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        rows = con.execute(
            """SELECT id, case_id, prediction_log_id, llm_response, model_used,
                      tokens_used, latency_ms, is_cached, error, created_at
               FROM copilot_logs ORDER BY id DESC LIMIT ?""",
            (int(limit),),
        ).fetchall()
        con.close()

        cols = ["id", "case_id", "prediction_log_id", "llm_response", "model_used",
                "tokens_used", "latency_ms", "is_cached", "error", "created_at"]
        return {"count": len(rows), "logs": [dict(zip(cols, r)) for r in rows]}
    except Exception as exc:
        return {"error": str(exc), "logs": []}