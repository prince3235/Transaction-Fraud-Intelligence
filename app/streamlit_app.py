import joblib
import streamlit as st

from src.features import build_features, load_feature_config
from src.risk_scoring import score_probability

st.set_page_config(page_title="Transaction Fraud Intelligence", layout="centered")
st.title("Transaction Fraud Intelligence System")

MODEL_PATH = "models/best_fraud_model.pkl"
CONFIG_PATH = "models/feature_config.json"

model = joblib.load(MODEL_PATH)
config = load_feature_config(CONFIG_PATH)

st.subheader("Enter a Transaction")

col1, col2 = st.columns(2)

with col1:
    step = st.number_input("step", min_value=0, value=10)
    ttype = st.selectbox("type", ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"])
    amount = st.number_input("amount", min_value=0.0, value=10000.0)
    oldbalanceOrg = st.number_input("oldbalanceOrg", min_value=0.0, value=50000.0)

with col2:
    newbalanceOrig = st.number_input("newbalanceOrig", min_value=0.0, value=40000.0)
    oldbalanceDest = st.number_input("oldbalanceDest", min_value=0.0, value=0.0)
    newbalanceDest = st.number_input("newbalanceDest", min_value=0.0, value=10000.0)

if st.button("Predict Risk"):
    tx = {
        "step": int(step),
        "type": ttype,
        "amount": float(amount),
        "oldbalanceOrg": float(oldbalanceOrg),
        "newbalanceOrig": float(newbalanceOrig),
        "oldbalanceDest": float(oldbalanceDest),
        "newbalanceDest": float(newbalanceDest),
    }

    X = build_features(tx, config)
    prob = float(model.predict_proba(X)[:, 1][0])

    risk = score_probability(prob)

    st.success("Prediction Complete")
    st.write({
        "fraud_probability": round(risk.probability, 4),
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,
        "recommended_action": risk.recommended_action
    })

    st.caption("Note: This is a demo risk scoring tool for educational purposes.")