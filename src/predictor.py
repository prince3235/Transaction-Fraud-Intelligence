"""
FraudPredictor — wraps the ML model with registry-aware loading.

Previously this class hardcoded `models/best_fraud_model.pkl`, bypassing the
model registry entirely. Now it consults `model_registry.get_active_model()`
for the pkl_path, falling back to the default path if the registry is empty.
This means promoting a model in the registry (and calling /admin/reload-model)
actually changes which model serves predictions.
"""
from __future__ import annotations

import logging
import joblib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.features import build_features, align_to_model_columns, load_json
from src.risk_scoring import score_probability

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]  # project root
DEFAULT_MODEL_PATH = BASE_DIR / "models" / "best_fraud_model.pkl"
CONFIG_PATH = BASE_DIR / "models" / "feature_config.json"
COLS_PATH = BASE_DIR / "models" / "feature_columns.json"


def _resolve_model_path() -> Tuple[Path, Optional[Dict[str, Any]]]:
    """Return (pkl_path, active_model_info) by consulting the registry."""
    try:
        from src.model_registry import get_active_model
        active = get_active_model(BASE_DIR)
        if active and active.get("pkl_path"):
            registered = Path(active["pkl_path"])
            if not registered.is_absolute():
                registered = BASE_DIR / registered
            if registered.exists():
                return registered, active
            logger.warning(
                "Active model %s pkl_path %s does not exist — falling back to default.",
                active.get("version"), registered,
            )
    except Exception as exc:
        logger.warning("Registry lookup failed, using default model path: %s", exc)
    return DEFAULT_MODEL_PATH, None


class FraudPredictor:
    def __init__(self):
        path, info = _resolve_model_path()
        logger.info("FraudPredictor loading model from %s (version=%s)",
                    path, (info or {}).get("version", "unknown"))
        self.model = joblib.load(path)
        self.model_path = path
        self.model_info = info
        self.config = load_json(CONFIG_PATH)
        self.model_columns = load_json(COLS_PATH)

    def reload(self) -> None:
        """Re-resolve the model path from the registry and reload."""
        path, info = _resolve_model_path()
        self.model = joblib.load(path)
        self.model_path = path
        self.model_info = info
        logger.info("FraudPredictor reloaded from %s (version=%s)",
                    path, (info or {}).get("version", "unknown"))

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
            "model_version": (self.model_info or {}).get("version", "unknown"),
        }
