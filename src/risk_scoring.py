from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskResult:
    probability: float
    risk_score: int
    risk_level: str
    recommended_action: str


def prob_to_risk_score(probability: float) -> int:
    if probability < 0:
        probability = 0.0
    if probability > 1:
        probability = 1.0
    return int(round(probability * 100))


def risk_level(score: int) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def recommended_action(level: str) -> str:
    level = level.upper()
    if level == "CRITICAL":
        return "HOLD transaction + immediate manual review"
    if level == "HIGH":
        return "Manual review required"
    if level == "MEDIUM":
        return "Allow but monitor / step-up verification"
    return "Allow"


def score_probability(probability: float) -> RiskResult:
    score = prob_to_risk_score(probability)
    level = risk_level(score)
    action = recommended_action(level)
    return RiskResult(
        probability=float(probability),
        risk_score=int(score),
        risk_level=str(level),
        recommended_action=str(action),
    )

LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
LEVEL_MIN_SCORE = {"LOW": 0, "MEDIUM": 40, "HIGH": 70, "CRITICAL": 85}

def _max_level(a: str, b: str) -> str:
    return a if LEVEL_ORDER[a] >= LEVEL_ORDER[b] else b

def policy_min_level_and_reasons(features: dict):
    min_level = "LOW"
    reasons = []

    ratio = features.get("amount_to_oldbalance_orig_ratio", 0)
    emptied = features.get("sender_account_emptied", 0)
    sig = features.get("suspicious_signal_count", 0)

    if ratio > 1 and emptied == 1:
        min_level = _max_level(min_level, "HIGH")
        reasons.append("Policy: Amount > sender balance + sender account emptied")

    if sig >= 3:
        min_level = _max_level(min_level, "MEDIUM")
        reasons.append("Policy: Multiple suspicious signals detected (>=3)")

    if sig >= 5:
        min_level = _max_level(min_level, "CRITICAL")
        reasons.append("Policy: Very high suspicious signal count (>=5)")

    if features.get("is_large_transaction", 0) == 1 and features.get("dest_received_large_amount", 0) == 1:
        min_level = _max_level(min_level, "HIGH")
        reasons.append("Policy: Large transaction + destination started from zero balance")

    return min_level, reasons

def apply_policy_overrides(risk_result, features: dict):
    min_level, reasons = policy_min_level_and_reasons(features)

    final_level = _max_level(risk_result.risk_level, min_level)
    bumped_score = max(risk_result.risk_score, LEVEL_MIN_SCORE[final_level])
    action = recommended_action(final_level)

    new_risk = RiskResult(
        probability=risk_result.probability,
        risk_score=bumped_score,
        risk_level=final_level,
        recommended_action=action
    )
    return new_risk, reasons