from pathlib import Path
import sys
import json
import time
from datetime import datetime, timezone

import pandas as pd
import joblib

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features import build_features, align_to_model_columns, load_json, TYPE_ENCODING
from src.risk_scoring import score_probability, apply_policy_overrides
from src.alerts import create_alert, should_alert
from src.storage import get_db_path, init_db, log_prediction

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = PROJECT_ROOT / "models" / "best_fraud_model.pkl"
CONFIG_PATH = PROJECT_ROOT / "models" / "feature_config.json"
COLS_PATH = PROJECT_ROOT / "models" / "feature_columns.json"
X_TEST_PATH = PROJECT_ROOT / "data" / "processed" / "X_test.csv"

model = joblib.load(MODEL_PATH)
config = load_json(CONFIG_PATH)
model_columns = load_json(COLS_PATH)

DB_PATH = get_db_path(PROJECT_ROOT)
init_db(DB_PATH)

# Create reverse mapping for type
TYPE_DECODING = {v: k for k, v in TYPE_ENCODING.items()}
# Fallback if encoding missing
TYPE_DECODING[-1] = "TRANSFER"

# Load test data
X_test = pd.read_csv(X_TEST_PATH)

# Sample rows for batch scoring
N = 5000
sample_df = X_test.sample(n=min(N, len(X_test)), random_state=42)

print(f"Starting batch scoring for {len(sample_df)} transactions...")

start = time.time()
for i, (_, row) in enumerate(sample_df.iterrows()):
    tx_dict = row.to_dict()

    # ✅ FIX: Reconstruct 'type' if missing
    if "type" not in tx_dict:
        encoded = tx_dict.get("type_encoded", -1)
        tx_dict["type"] = TYPE_DECODING.get(int(encoded), "TRANSFER")

    # Ensure all required raw fields exist (fallback to 0 if missing)
    required = ["step", "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"]
    for key in required:
        if key not in tx_dict:
            tx_dict[key] = 0.0

    try:
        # Build features
        X = build_features(tx_dict, config)
        X = align_to_model_columns(X, model_columns)

        # Predict
        ml_prob = float(model.predict_proba(X)[:, 1][0])
        base_risk = score_probability(ml_prob)

        features_dict = X.iloc[0].to_dict()
        policy_out = apply_policy_overrides(base_risk, features_dict)

        if isinstance(policy_out, tuple):
            final_risk, policy_reasons = policy_out
        else:
            final_risk, policy_reasons = policy_out, []

        # Alert
        alert = None
        if should_alert(final_risk.risk_level, min_level="MEDIUM"):
            alert_obj = create_alert(
                transaction_ref=f"batch_{i}",
                probability=final_risk.probability,
                risk_score=final_risk.risk_score,
                risk_level=final_risk.risk_level,
                recommended_action=final_risk.recommended_action,
                reasons=[{"reason": r} for r in policy_reasons],
            )
            alert = alert_obj.__dict__

        # Log
        created_at = datetime.now(timezone.utc).isoformat()
        log_prediction(
            db_path=DB_PATH,
            created_at=created_at,
            transaction=tx_dict,
            ml_probability=ml_prob,
            ml_risk_level=base_risk.risk_level,
            ml_risk_score=base_risk.risk_score,
            final_risk_level=final_risk.risk_level,
            final_risk_score=final_risk.risk_score,
            policy_override_applied=(final_risk.risk_level != base_risk.risk_level),
            policy_reasons=policy_reasons,
            suspicious_signal_count=int(features_dict.get("suspicious_signal_count", 0)),
            alert=alert,
        )

        if (i + 1) % 500 == 0:
            print(f"Processed {i+1}/{len(sample_df)}")

    except Exception as e:
        print(f"Error at row {i}: {e}")
        continue

elapsed = time.time() - start
print(f"Batch scoring complete in {elapsed:.2f}s. Logs saved to DB.")