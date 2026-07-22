import asyncio
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
from sqlalchemy import func

logger = logging.getLogger(__name__)

from src.features import build_features, align_to_model_columns, load_json
from src.risk_scoring import score_probability, apply_policy_overrides
from src.alerts import create_alert, should_alert
from src.storage import get_db_path, init_db, log_prediction, fetch_recent_logs
from src.auth import authenticate, has_permission, create_access_token, decode_access_token
from src.rules_engine import evaluate_rules
from src.db import SessionLocal
from src.models import PredictionLog, CopilotLog

# Default Anthropic model — env-overridable.
ANTHROPIC_MODEL_NAME = os.environ.get(
    "ANTHROPIC_MODEL", "claude-sonnet-4-5"
)

app = FastAPI(title="Transaction Fraud Intelligence API", version="1.1.0")

# ── CORS middleware ─────────────────────────────────────────────────────────
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
    Supports JWT tokens, static API_AUTH_TOKEN, and demo username:password fallback.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials

    # 1. Static API Token check (constant-time)
    api_token = os.environ.get("API_AUTH_TOKEN", "")
    if api_token:
        import hmac
        if hmac.compare_digest(token, api_token):
            return {"id": 0, "username": "api-client", "role": "Admin"}

    # 2. Standard JWT token decoding & validation
    jwt_payload = decode_access_token(token)
    if jwt_payload and isinstance(jwt_payload, dict):
        username = jwt_payload.get("sub") or jwt_payload.get("username")
        if username:
            return {
                "id": jwt_payload.get("id", 0),
                "username": username,
                "role": jwt_payload.get("role", "Viewer"),
            }

    # 3. Demo username:password token fallback
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


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
def login(req: LoginRequest):
    """Authenticate user credentials and issue a signed JWT access token."""
    user = authenticate(DB_PATH, req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_payload = {
        "sub": user["username"],
        "id": user["id"],
        "role": user["role"],
    }
    access_token = create_access_token(token_payload)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


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
    import numpy as np
    raw_probs = model.predict_proba(X)
    ml_prob = float(np.asarray(raw_probs)[:, 1][0])
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
async def predict(tx: TransactionIn, user: dict = Depends(get_current_user)):
    tx_dict = tx.model_dump()
    loop = asyncio.get_running_loop()
    X, ml_prob, base_risk, final_risk, policy_reasons, alert, ssc, rule_hits = await loop.run_in_executor(
        None, score_tx, tx_dict
    )

    created_at = datetime.now(timezone.utc).isoformat()

    # Log to database via storage helper
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
        "ml_probability": ml_prob,
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
async def debug_predict(tx: TransactionIn, user: dict = Depends(get_current_user)):
    tx_dict = tx.model_dump()
    loop = asyncio.get_running_loop()
    X, ml_prob, base_risk, final_risk, policy_reasons, alert, ssc, rule_hits = await loop.run_in_executor(
        None, score_tx, tx_dict
    )

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

    X_TEST_PATH = BASE_DIR / "data" / "processed" / "X_test.csv"
    X_test = pd.read_csv(X_TEST_PATH)

    sample_df = X_test.sample(n=min(count, len(X_test)), random_state=42)
    sample_df = sample_df[model_columns]

    ml_probs = model.predict_proba(sample_df)[:, 1]
    
    import random
    from datetime import timedelta
    offset_minutes = random.randint(0, 60*24*7)
    created_at = (datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)).isoformat()

    db_objects = []
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

        log_entry = PredictionLog(
            created_at=created_at,
            transaction_json=tx,
            ml_probability=float(ml_prob),
            ml_risk_level=str(base_risk.risk_level),
            ml_risk_score=int(base_risk.risk_score),
            final_risk_level=str(final_risk.risk_level),
            final_risk_score=int(final_risk.risk_score),
            policy_override_applied=(final_risk.risk_level != base_risk.risk_level),
            policy_reasons_json=policy_reasons,
            suspicious_signal_count=int(features_dict.get("suspicious_signal_count", 0)),
            alert_json=alert,
            status="APPROVED" if final_risk.risk_level == "LOW" else "PENDING_REVIEW",
        )
        db_objects.append(log_entry)

    db = SessionLocal()
    try:
        db.bulk_save_objects(db_objects)
        db.commit()
        return {"status": "ok", "inserted": len(db_objects)}
    finally:
        db.close()


class ActionIn(BaseModel):
    status: str

@app.post("/logs/{log_id}/action")
def log_action(log_id: int, action: ActionIn, user: dict = Depends(require_permission("manage_cases"))):
    if action.status not in ("APPROVED", "BLOCKED"):
        raise HTTPException(status_code=422, detail="Invalid status — must be APPROVED or BLOCKED")
    
    db = SessionLocal()
    try:
        log_entry = db.query(PredictionLog).filter(PredictionLog.id == int(log_id)).first()
        if not log_entry:
            raise HTTPException(status_code=404, detail="Log entry not found")
        log_entry.status = action.status
        db.commit()
        return {"status": "ok", "id": log_id, "new_status": action.status}
    finally:
        db.close()

# ========== ADMIN & MONITORING ENDPOINTS ==========

@app.get("/stats")
def get_stats(user: dict = Depends(get_current_user)):
    """Get system-level statistics for monitoring using ORM."""
    db = SessionLocal()
    try:
        total = db.query(func.count(PredictionLog.id)).scalar() or 0
        
        dist_query = (
            db.query(PredictionLog.final_risk_level, func.count(PredictionLog.id))
            .group_by(PredictionLog.final_risk_level)
            .all()
        )
        risk_dist = [{"final_risk_level": level, "count": count} for level, count in dist_query]
        
        override_count = db.query(func.count(PredictionLog.id)).filter(PredictionLog.policy_override_applied == True).scalar() or 0
        override_rate = (override_count / total * 100.0) if total > 0 else 0.0
        
        avg_score = db.query(func.avg(PredictionLog.final_risk_score)).scalar() or 0.0
        
        return {
            "total_scored": total,
            "risk_distribution": risk_dist,
            "override_rate_pct": round(float(override_rate), 2),
            "avg_risk_score": round(float(avg_score), 2)
        }
    finally:
        db.close()


@app.get("/logs/{log_id}/explain")
def explain_log(log_id: int, user: dict = Depends(get_current_user)):
    """Get detailed explanation for a specific log entry using ORM."""
    db = SessionLocal()
    try:
        log_entry = db.query(PredictionLog).filter(PredictionLog.id == int(log_id)).first()
        if not log_entry:
            return {"error": "log not found"}
        
        tx_data = log_entry.transaction_json if isinstance(log_entry.transaction_json, dict) else json.loads(log_entry.transaction_json or "{}")
        reasons_data = log_entry.policy_reasons_json if isinstance(log_entry.policy_reasons_json, (list, dict)) else json.loads(log_entry.policy_reasons_json or "[]")

        return {
            "log_id": log_id,
            "transaction": tx_data,
            "ml": {
                "probability": log_entry.ml_probability,
                "level": log_entry.ml_risk_level,
                "score": log_entry.ml_risk_score
            },
            "final": {
                "level": log_entry.final_risk_level,
                "score": log_entry.final_risk_score
            },
            "override_applied": bool(log_entry.policy_override_applied),
            "override_reasons": reasons_data,
            "explanation": "ML model assessed base risk. Policy engine may have elevated it based on business rules."
        }
    finally:
        db.close()


# ========== LLM COPILOT ENDPOINTS ==========

class CopilotRequest(BaseModel):
    prediction_log_id: Optional[int] = None
    case_id: Optional[str] = None
    follow_up: Optional[str] = None

    class Config:
        pass


@app.post("/copilot/explain")
def copilot_explain(req: CopilotRequest, user: dict = Depends(get_current_user)):
    """
    Generate a natural-language explanation for a flagged transaction.

    Accepts either { "prediction_log_id": int } or { "case_id": str }.
    Optionally include { "follow_up": "Has this user been flagged before?" }
    for follow-up questions.
    """
    if not req.prediction_log_id and not req.case_id:
        return {"error": "Either prediction_log_id or case_id is required.", "explanation": None}

    try:
        from src.llm_copilot import CopilotEngine
        from src.db_migrations import run_migrations

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
    """Fetch recent copilot query audit logs using ORM."""
    db = SessionLocal()
    try:
        logs = db.query(CopilotLog).order_by(CopilotLog.id.desc()).limit(int(limit)).all()
        log_list = [{
            "id": l.id,
            "case_id": l.case_id,
            "prediction_log_id": l.prediction_log_id,
            "llm_response": l.llm_response,
            "model_used": l.model_used,
            "tokens_used": l.tokens_used,
            "latency_ms": l.latency_ms,
            "is_cached": l.is_cached,
            "error": l.error,
            "created_at": l.created_at
        } for l in logs]
        return {"count": len(log_list), "logs": log_list}
    except Exception as exc:
        return {"error": str(exc), "logs": []}
    finally:
        db.close()