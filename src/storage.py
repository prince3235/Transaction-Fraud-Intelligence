from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.db import SessionLocal, engine
from src.models import Base, PredictionLog

def get_db_path(base_dir: Path = None) -> Path:
    # Kept for backward compatibility if any module imports it
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "app_db" / "fraud_intelligence.db"

def init_db(db_path: Path = None) -> None:
    # Now Alembic handles schema generation, but for tests or fallback:
    Base.metadata.create_all(bind=engine)

def log_prediction(
    db_path: Path, # Ignored, kept for signature compat
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
    status: Optional[str] = None,
) -> None:
    db = SessionLocal()
    try:
        log = PredictionLog(
            created_at=created_at,
            transaction_json=transaction,
            ml_probability=float(ml_probability),
            ml_risk_level=str(ml_risk_level),
            ml_risk_score=int(ml_risk_score),
            final_risk_level=str(final_risk_level),
            final_risk_score=int(final_risk_score),
            policy_override_applied=policy_override_applied,
            policy_reasons_json=policy_reasons,
            suspicious_signal_count=int(suspicious_signal_count) if suspicious_signal_count is not None else None,
            alert_json=alert,
            status=status if status is not None else ("APPROVED" if final_risk_level == "LOW" else "PENDING_REVIEW")
        )
        db.add(log)
        db.commit()
    finally:
        db.close()

def fetch_recent_logs(db_path: Path, limit: int = 50) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        logs = db.query(PredictionLog).order_by(PredictionLog.id.desc()).limit(limit).all()
        out = []
        for r in logs:
            out.append(
                {
                    "id": r.id,
                    "created_at": r.created_at,
                    "transaction": r.transaction_json,
                    "ml_probability": r.ml_probability,
                    "ml_risk_level": r.ml_risk_level,
                    "ml_risk_score": r.ml_risk_score,
                    "final_risk_level": r.final_risk_level,
                    "final_risk_score": r.final_risk_score,
                    "policy_override_applied": r.policy_override_applied,
                    "policy_reasons": r.policy_reasons_json,
                    "suspicious_signal_count": r.suspicious_signal_count,
                    "alert": r.alert_json,
                    "status": r.status,
                }
            )
        return out
    finally:
        db.close()