from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # pages folder ke liye parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import requests
import streamlit as st

st.set_page_config(page_title="Transaction Simulator", layout="wide")
st.title("Transaction Simulator")
st.caption("Try custom transactions and generate logs for monitoring dashboard.")

API_BASE = st.sidebar.text_input("API Base URL", "http://127.0.0.1:8000")

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

payload = {
    "step": int(step),
    "type": ttype,
    "amount": float(amount),
    "oldbalanceOrg": float(oldbalanceOrg),
    "newbalanceOrig": float(newbalanceOrig),
    "oldbalanceDest": float(oldbalanceDest),
    "newbalanceDest": float(newbalanceDest),
}

c1, c2 = st.columns(2)
with c1:
    if st.button("Predict (and Log)"):
        try:
            r = requests.post(f"{API_BASE}/predict", json=payload, timeout=30)
            st.write("Status:", r.status_code)
            st.json(r.json())
        except requests.exceptions.ConnectionError:
            st.error("API not reachable. Start FastAPI: python -m uvicorn api.main:app --reload")

with c2:
    if st.button("Debug Predict (features + reasons)"):
        try:
            r = requests.post(f"{API_BASE}/debug/predict", json=payload, timeout=30)
            st.write("Status:", r.status_code)
            st.json(r.json())
        except requests.exceptions.ConnectionError:
            st.error("API not reachable. Start FastAPI: python -m uvicorn api.main:app --reload")