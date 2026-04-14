from __future__ import annotations

import joblib
from pathlib import Path
from typing import Any, Dict

from src.features import build_features, align_to_model_columns, load_json
from src.risk_scoring import score_probability

BASE_DIR = Path(__file__).resolve().parents[1]  # project root


class FraudPredictor:
    def __init__(self):
        self.model = joblib.load(BASE_DIR / "models" / "best_fraud_model.pkl")
        self.config = load_json(BASE_DIR / "models" / "feature_config.json")
        self.model_columns = load_json(BASE_DIR / "models" / "feature_columns.json")

    def predict(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        X = build_features(tx, self.config)
        X = align_to_model_columns(X, self.model_columns)

        prob = float(self.model.predict_proba(X)[:, 1][0])
        risk = score_probability(prob)

        return {
            "fraud_probability": risk.probability,
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "recommended_action": risk.recommended_action,
        }