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

    # 2) Model probability
    prob = float(model.predict_proba(X)[:, 1][0])

    # 3) Base risk scoring
    risk = score_probability(prob)

    # 4) Policy override (rule-based guardrails)
    features_dict = X.iloc[0].to_dict()
    risk = apply_policy_overrides(risk, features_dict)

    # 5) Create alert if needed
    alert = None
    if should_alert(risk.risk_level, min_level="MEDIUM"):
        alert_obj = create_alert(
            transaction_ref="api_input",
            probability=risk.probability,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            recommended_action=risk.recommended_action,
            reasons=[],
        )
        alert = alert_obj.__dict__

    return {
        "fraud_probability": risk.probability,
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,
        "recommended_action": risk.recommended_action,
        "alert": alert,
    }