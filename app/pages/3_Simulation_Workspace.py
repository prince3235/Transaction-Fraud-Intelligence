import streamlit as st
import requests
import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.simulator import build_transaction
from app.auth_guard import require_auth, display_user_profile

st.set_page_config(page_title="Simulation Workspace", page_icon="🧪", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_dashboard")

with st.sidebar:
    display_user_profile()

st.markdown("""
<div style="padding:1rem 0 1.5rem">
  <div class="page-title">
    Simulation <span class="gradient-word">Workspace</span>
  </div>
  <div class="page-subtitle">
    Inject raw transactions into the ML pipeline and analyze the real-time API response.
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="hdivider"></div>', unsafe_allow_html=True)

# ── PRESETS ────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Payload Builder</div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1.5])

with col1:
    preset = st.selectbox("Load Preset Scenario", [
        "Standard Transfer", 
        "High-Velocity Attack", 
        "Account Takeover (ATO) Attempt", 
        "Suspicious Merchant",
        "Custom"
    ])
    
    # Defaults
    amt = 5000.0
    m_type = "POS Retail"
    c_try = "India"
    hr = 14
    sig = 0
    new_dev = False
    vel = False
    
    if preset == "High-Velocity Attack":
        amt = 85000.0
        hr = 3
        sig = 4
        vel = True
        c_try = "Anonymous VPN"
    elif preset == "Account Takeover (ATO) Attempt":
        amt = 99999.0
        m_type = "Crypto Exchange"
        new_dev = True
        sig = 3
    elif preset == "Suspicious Merchant":
        amt = 45000.0
        m_type = "Gambling"
        c_try = "Russia"
        sig = 2
        
    amount = st.slider("Amount (₹)", min_value=100.0, max_value=200000.0, value=amt, step=1000.0)
    merchant_type = st.selectbox("Merchant Type", ["POS Retail", "E-Commerce", "ATM Withdrawal", "Wire Transfer", "Crypto Exchange", "Gambling", "Utility Bill", "Travel Agency"], index=["POS Retail", "E-Commerce", "ATM Withdrawal", "Wire Transfer", "Crypto Exchange", "Gambling", "Utility Bill", "Travel Agency"].index(m_type))
    country = st.selectbox("Country", ["India", "USA", "UK", "Germany", "UAE", "Brazil", "China", "Russia", "Nigeria", "Anonymous VPN"], index=["India", "USA", "UK", "Germany", "UAE", "Brazil", "China", "Russia", "Nigeria", "Anonymous VPN"].index(c_try))
    hour = st.slider("Transaction Hour (24h)", 0, 23, value=int(hr))
    
    suspicious_signals = st.slider("Suspicious Signals (Velocity, IP mismatch, etc)", 0, 5, value=int(sig))
    
    c_ck1, c_ck2 = st.columns(2)
    with c_ck1:
        is_new_device = st.checkbox("New Device Detected", value=new_dev)
    with c_ck2:
        velocity_flag = st.checkbox("High Velocity Flag", value=vel)
        
    st.markdown('<br>', unsafe_allow_html=True)
    inject_btn = st.button("🚀 Send to Prediction API", type="primary", use_container_width=True)

with col2:
    st.markdown('<div class="section-label">API Request Payload</div>', unsafe_allow_html=True)
    
    # We use simulator logic to build the raw dictionary
    # Then we map it to our API model
    sim_txn = build_transaction(amount, merchant_type, country, hour, suspicious_signals, is_new_device, velocity_flag, 1)
    
    api_payload = {
        "step": sim_txn.get("step", 1),
        "type": "TRANSFER" if merchant_type in ["Wire Transfer", "Crypto Exchange"] else "PAYMENT",
        "amount": amount,
        "oldbalanceOrg": sim_txn.get("oldbalanceOrg", 10000.0),
        "newbalanceOrig": max(0, sim_txn.get("oldbalanceOrg", 10000.0) - amount),
        "oldbalanceDest": sim_txn.get("oldbalanceDest", 500.0),
        "newbalanceDest": sim_txn.get("oldbalanceDest", 500.0) + amount
    }
    
    # We also add the mock "enrichment" features that our API might read or backend logic might build.
    # Actually, our API takes exactly TransactionIn: step, type, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest
    
    st.json(api_payload)
    
    st.markdown('<div class="section-label">API Response</div>', unsafe_allow_html=True)
    
    if inject_btn:
        with st.spinner("Processing transaction..."):
            try:
                res = requests.post("http://localhost:8000/predict", json=api_payload, timeout=3)
                if res.status_code == 200:
                    data = res.json()
                    
                    st.success("200 OK")
                    st.json(data)
                    
                    if data.get("alert"):
                        st.error("🚨 ALERT TRIGGERED AND LOGGED TO QUEUE")
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Failed to connect to API. Is backend running? Exception: {e}")
    else:
        st.info("Awaiting injection...")