import requests
import pandas as pd
import streamlit as st

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Fraud Intelligence Dashboard", layout="wide")
st.title("Transaction Fraud Intelligence – Monitoring Dashboard")

tab1, tab2, tab3 = st.tabs(["Score Transaction", "Recent Logs", "Debug Scoring"])

with tab1:
    st.subheader("Score a new transaction")
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

    if st.button("Predict & Log"):
        r = requests.post(f"{API_BASE}/predict", json=payload, timeout=30)
        st.write("Status:", r.status_code)
        st.json(r.json())


with tab2:
    st.subheader("Recent prediction logs")
    limit = st.slider("limit", 10, 300, 50)

    if st.button("Refresh Logs"):
        r = requests.get(f"{API_BASE}/logs/recent", params={"limit": limit}, timeout=30)
        data = r.json()["items"]
        df = pd.json_normalize(data)
        st.dataframe(df, use_container_width=True)


with tab3:
    st.subheader("Debug scoring (see engineered features + policy reasons)")
    if st.button("Run Debug"):
        r = requests.post(f"{API_BASE}/debug/predict", json=payload, timeout=30)
        st.write("Status:", r.status_code)
        st.json(r.json())