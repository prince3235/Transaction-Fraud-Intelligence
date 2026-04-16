from pathlib import Path

import joblib
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.features import build_features, align_to_model_columns, load_json
from src.risk_scoring import score_probability, apply_policy_overrides
from src.alerts import create_alert, should_alert

app = FastAPI(title="Transaction Fraud Intelligence API", version="1.0.0")

BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = BASE_DIR / "models" / "best_fraud_model.pkl"
CONFIG_PATH = BASE_DIR / "models" / "feature_config.json"
COLS_PATH = BASE_DIR / "models" / "feature_columns.json"

model = joblib.load(MODEL_PATH)
config = load_json(CONFIG_PATH)
model_columns = load_json(COLS_PATH)


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
    return {"status": "ok"}


@app.post("/predict")
def predict(tx: TransactionIn):
    # 1) Build + align features
    X = build_features(tx.model_dump(), config)
    X = align_to_model_columns(X, model_columns)

    # 2) ML probability
    ml_prob = float(model.predict_proba(X)[:, 1][0])

    # 3) Base risk from ML
    base_risk = score_probability(ml_prob)

    # 4) Policy override (may return RiskResult OR (RiskResult, reasons))
    features_dict = X.iloc[0].to_dict()
    policy_out = apply_policy_overrides(base_risk, features_dict)

    if isinstance(policy_out, tuple):
        final_risk, policy_reasons = policy_out
    else:
        final_risk, policy_reasons = policy_out, []

    # 5) Create alert if needed
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

    # 6) Return both ML + Final (business) outputs
    return {
        "ml_probability": round(ml_prob, 6),
        "ml_risk_score": base_risk.risk_score,
        "ml_risk_level": base_risk.risk_level,
        "final_risk_score": final_risk.risk_score,
        "final_risk_level": final_risk.risk_level,
        "recommended_action": final_risk.recommended_action,
        "policy_override_applied": (final_risk.risk_level != base_risk.risk_level),
        "policy_reasons": policy_reasons,
        "alert": alert,
    }