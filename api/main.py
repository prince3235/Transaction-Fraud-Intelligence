from __future__ import annotations

import joblib
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.features import build_features, load_feature_config
from src.risk_scoring import score_probability
from src.alerts import create_alert, should_alert

app = FastAPI(title="Transaction Fraud Intelligence API", version="1.0.0")

MODEL_PATH = "../models/best_fraud_model.pkl"

model = joblib.load(MODEL_PATH)
config = load_feature_config("../models/feature_config.json")


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
    X = build_features(tx.model_dump(), config)

    prob = float(model.predict_proba(X)[:, 1][0])
    risk = score_probability(prob)

    # alert creation (only if MEDIUM+)
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
        "probability": risk.probability,
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,
        "recommended_action": risk.recommended_action,
        "alert": alert,
    }