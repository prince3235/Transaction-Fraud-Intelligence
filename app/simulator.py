"""
simulator.py  ─  Fraud Transaction Simulation Engine
Generates realistic transactions with ML-style risk scoring.
"""

import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# ── Risk signal weights (mirrors a real ML feature set) ─────────────────────
_MERCHANT_RISK = {
    "E-Commerce":      0.15,
    "Crypto Exchange": 0.72,
    "ATM Withdrawal":  0.45,
    "POS Retail":      0.08,
    "Wire Transfer":   0.55,
    "Gambling":        0.68,
    "Utility Bill":    0.04,
    "Travel Agency":   0.22,
}

_COUNTRY_RISK = {
    "India":          0.10,
    "USA":            0.12,
    "Nigeria":        0.78,
    "Russia":         0.70,
    "UK":             0.14,
    "UAE":            0.35,
    "Brazil":         0.42,
    "Germany":        0.09,
    "China":          0.38,
    "Anonymous VPN":  0.90,
}

_HOUR_RISK = {          # 0–3 = night spike
    range(0,  4):  0.70,
    range(4,  8):  0.20,
    range(8, 18):  0.05,
    range(18, 21): 0.15,
    range(21, 24): 0.45,
}


def _hour_risk_score(hour: int) -> float:
    for rng, score in _HOUR_RISK.items():
        if hour in rng:
            return score
    return 0.10


def compute_ml_probability(
    amount: float,
    merchant_type: str,
    country: str,
    hour: int,
    suspicious_signals: int,
    is_new_device: bool,
    velocity_flag: bool,
) -> float:
    """Weighted logistic-style score → [0, 1]."""
    score = 0.0
    score += _MERCHANT_RISK.get(merchant_type, 0.20) * 0.25
    score += _COUNTRY_RISK.get(country, 0.30)        * 0.20
    score += _hour_risk_score(hour)                   * 0.15
    score += min(amount / 100_000, 1.0)               * 0.20
    score += min(suspicious_signals / 5, 1.0)         * 0.12
    score += (0.05 if is_new_device  else 0.0)
    score += (0.03 if velocity_flag  else 0.0)

    # Add small jitter so repeated identical inputs vary slightly
    score = np.clip(score + random.gauss(0, 0.02), 0.0, 1.0)
    return round(float(score), 4)


def risk_level_from_score(final_score: int) -> str:
    if final_score >= 85:  return "CRITICAL"
    if final_score >= 60:  return "HIGH"
    if final_score >= 35:  return "MEDIUM"
    return "LOW"


def build_transaction(
    amount: float,
    merchant_type: str,
    country: str,
    hour: int,
    suspicious_signals: int,
    is_new_device: bool,
    velocity_flag: bool,
    sim_id: int,
) -> dict:
    """Return a single transaction dict compatible with the dashboard df schema."""
    ml_prob = compute_ml_probability(
        amount, merchant_type, country, hour,
        suspicious_signals, is_new_device, velocity_flag,
    )

    ml_risk_level = risk_level_from_score(int(ml_prob * 100))

    # Policy engine
    policy_reasons = []
    if suspicious_signals >= 3:
        policy_reasons.append(f"Policy: Multiple suspicious signals detected (>={suspicious_signals})")
    if amount > 50_000:
        policy_reasons.append("Policy: Amount > sender balance + sender account emptied")
    if velocity_flag:
        policy_reasons.append("Policy: High velocity flag triggered")
    if country in ("Nigeria","Russia","Anonymous VPN"):
        policy_reasons.append(f"Policy: High-risk country — {country}")
    if hour in range(0, 4):
        policy_reasons.append("Policy: Transaction in high-risk night window (00-04)")

    override = len(policy_reasons) > 0
    # Override can bump risk level up
    final_score = int(ml_prob * 100)
    if override:
        final_score = min(100, final_score + len(policy_reasons) * 5)

    final_level = risk_level_from_score(final_score)

    return {
        "id":                       f"SIM-{sim_id:04d}",
        "created_at":               datetime.now() - timedelta(seconds=random.randint(0, 300)),
        "ml_probability":           ml_prob,
        "ml_risk_level":            ml_risk_level,
        "final_risk_level":         final_level,
        "final_risk_score":         final_score,
        "policy_override_applied":  int(override),
        "policy_reasons":           policy_reasons,
        # Extra fields for the live feed display
        "amount":                   round(amount, 2),
        "merchant_type":            merchant_type,
        "country":                  country,
        "_is_simulated":            True,
    }


def batch_simulate(
    n: int = 10,
    start_id: int = 9000,
    high_risk_ratio: float = 0.4,
) -> list[dict]:
    """Generate n random transactions. high_risk_ratio controls fraud mix."""
    txns = []
    merchants = list(_MERCHANT_RISK.keys())
    countries  = list(_COUNTRY_RISK.keys())

    for i in range(n):
        is_fraud = random.random() < high_risk_ratio
        if is_fraud:
            merchant  = random.choice(["Crypto Exchange","Gambling","Wire Transfer","ATM Withdrawal"])
            country   = random.choice(["Nigeria","Russia","Anonymous VPN","UAE"])
            amount    = random.uniform(5_000, 95_000)
            hour      = random.choice([0,1,2,22,23])
            signals   = random.randint(2, 5)
            new_dev   = random.random() > 0.3
            velocity  = random.random() > 0.4
        else:
            merchant  = random.choice(["POS Retail","Utility Bill","E-Commerce","Travel Agency"])
            country   = random.choice(["India","USA","UK","Germany"])
            amount    = random.uniform(100, 8_000)
            hour      = random.randint(8, 20)
            signals   = random.randint(0, 1)
            new_dev   = False
            velocity  = False

        txns.append(build_transaction(
            amount, merchant, country, hour,
            signals, new_dev, velocity,
            sim_id=start_id + i,
        ))
    return txns