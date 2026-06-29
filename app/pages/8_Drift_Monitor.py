import streamlit as st
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path, load_logs_df
from src.drift_monitor import calculate_psi, record_drift_snapshot, get_latest_drift_snapshots
from src.auth import log_audit_event

st.set_page_config(page_title="Data Drift Monitor", page_icon="📊", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_model")
user = st.session_state.user
DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Data Drift <span class="gradient-word">Monitor</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Track Population Stability Index (PSI) to detect when model inputs change</div>', unsafe_allow_html=True)


# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_data():
    # In a real system, training data would be loaded from a feature store.
    # Here we simulate baseline and production distributions using recent logs vs older logs
    df = load_logs_df(DB_PATH, limit=5000)
    if df.empty:
        return None, None
        
    df = df.sort_values('id')
    midpoint = len(df) // 2
    if midpoint < 100:
        return None, None
        
    baseline = df.iloc[:midpoint]
    production = df.iloc[midpoint:]
    return baseline, production

baseline_df, prod_df = fetch_data()

if baseline_df is None or prod_df is None:
    st.info("Insufficient data for drift analysis. Need at least 200 logs.")
    st.stop()


# ── Run Analysis ──────────────────────────────────────────────────────────────
features_to_monitor = [
    ("ml_probability", "Model Probability"),
    ("ml_risk_score", "Risk Score"),
    ("amount", "Transaction Amount")
]

# We need to extract 'amount' from the transaction JSON
baseline_df['amount'] = baseline_df['transaction'].apply(lambda x: float(x.get('amount', 0)))
prod_df['amount']     = prod_df['transaction'].apply(lambda x: float(x.get('amount', 0)))

snapshots = get_latest_drift_snapshots(DB_PATH)
if not snapshots or st.sidebar.button("🔄 Run PSI Scan Now"):
    with st.spinner("Calculating Population Stability Index..."):
        snapshots = []
        for col, label in features_to_monitor:
            base_data = baseline_df[col].dropna().values
            prod_data = prod_df[col].dropna().values
            snap = record_drift_snapshot(DB_PATH, label, base_data, prod_data)
            snapshots.append(snap)
        log_audit_event(DB_PATH, user["username"], "Drift Scan Executed", "drift_snapshots")
        st.sidebar.success("Scan complete!")

# ── Metrics Row ───────────────────────────────────────────────────────────────
cols = st.columns(len(features_to_monitor))
for i, snap in enumerate(snapshots):
    psi = snap['psi_score']
    label = snap['feature_name']
    
    status = "Stable"
    color = "#00E676"
    if psi > 0.2:
        status = "Drift Detected"
        color = "#FF2D55"
    elif psi > 0.1:
        status = "Warning"
        color = "#FF8A00"
        
    with cols[i]:
        st.markdown(f"""
        <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);
                    border-radius:12px;padding:20px;border-top:4px solid {color};">
            <div style="font-size:12px;color:#8899AA;text-transform:uppercase;margin-bottom:8px;">{label}</div>
            <div style="display:flex;align-items:end;gap:10px;margin-bottom:10px;">
                <span style="font-size:32px;font-weight:800;color:#E8F0FF;line-height:1;">{psi:.3f}</span>
                <span style="font-size:13px;font-weight:700;color:{color};padding-bottom:4px;">{status}</span>
            </div>
            <div style="font-size:11px;color:#BAC4D0;">
                Baseline Mean: {snap['baseline_mean']:.2f} <br>
                Current Mean: {snap['current_mean']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── Distribution Charts ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-label">Distribution Comparisons</div>', unsafe_allow_html=True)

for col, label in features_to_monitor:
    st.markdown(f"#### {label}")
    
    base_data = baseline_df[col].dropna().values
    prod_data = prod_df[col].dropna().values
    
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=base_data, name="Baseline (Training)", opacity=0.7, marker_color="#00B4FF", histnorm='probability density'))
    fig.add_trace(go.Histogram(x=prod_data, name="Current (Production)", opacity=0.7, marker_color="#FF8A00", histnorm='probability density'))
    
    fig.update_layout(
        barmode='overlay',
        height=300,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8899AA"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    if col == "amount":
        fig.update_xaxes(type="log", title_text="Amount (Log Scale)")
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
