from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Alert:
    alert_id: str
    created_at: str
    transaction_ref: str
    risk_level: str
    risk_score: int
    probability: float
    recommended_action: str
    reasons: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "PENDING_REVIEW"


def make_alert_id(prefix: str = "ALT") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{ts}"


def create_alert(
    transaction_ref: str,
    probability: float,
    risk_score: int,
    risk_level: str,
    recommended_action: str,
    reasons: Optional[List[Dict[str, Any]]] = None,
) -> Alert:
    return Alert(
        alert_id=make_alert_id(),
        created_at=datetime.now(timezone.utc).isoformat(),
        transaction_ref=str(transaction_ref),
        risk_level=str(risk_level),
        risk_score=int(risk_score),
        probability=float(probability),
        recommended_action=str(recommended_action),
        reasons=reasons or [],
    )


def should_alert(risk_level: str, min_level: str = "MEDIUM") -> bool:
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    return order[risk_level.upper()] >= order[min_level.upper()]