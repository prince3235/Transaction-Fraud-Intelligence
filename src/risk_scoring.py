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
