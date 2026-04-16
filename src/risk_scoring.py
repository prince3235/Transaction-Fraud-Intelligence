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

def apply_policy_overrides(risk_result, features: dict):
    """
    risk_result: RiskResult (from score_probability)
    features: single-row feature dict (engineered)
    """

    min_level = "LOW"

    # Rule 1: Amount way higher than sender balance + account emptied
    if features.get("amount_to_oldbalance_orig_ratio", 0) > 1 and features.get("sender_account_emptied", 0) == 1:
        min_level = _max_level(min_level, "HIGH")

    # Rule 2: Too many suspicious signals
    if features.get("suspicious_signal_count", 0) >= 3:
        min_level = _max_level(min_level, "MEDIUM")

    if features.get("suspicious_signal_count", 0) >= 5:
        min_level = _max_level(min_level, "CRITICAL")

    # Rule 3: Large transaction + destination started from zero
    if features.get("is_large_transaction", 0) == 1 and features.get("dest_received_large_amount", 0) == 1:
        min_level = _max_level(min_level, "HIGH")

    final_level = _max_level(risk_result.risk_level, min_level)

    # bump score to at least min score of that level
    bumped_score = max(risk_result.risk_score, LEVEL_MIN_SCORE[final_level])

    # update action according to final_level
    action = recommended_action(final_level)

    return RiskResult(
        probability=risk_result.probability,
        risk_score=bumped_score,
        risk_level=final_level,
        recommended_action=action
    )
    
