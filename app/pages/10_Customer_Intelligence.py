import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path, load_logs_df
from src.customer_profile import get_or_create_customer_profile, search_customers
from src.auth import log_audit_event

st.set_page_config(page_title="Customer Intelligence", page_icon="👤", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_cases")
user = st.session_state.user
DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Customer <span class="gradient-word">Intelligence</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">360-degree risk profiling and historical behavior analysis</div>', unsafe_allow_html=True)


# ── Search Bar ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Find Customer</div>', unsafe_allow_html=True)
search_query = st.text_input("Enter Customer ID (e.g., C12345...)", placeholder="Search by exact or partial ID...")

if not search_query:
    # Show a few top risk customers as suggestions
    st.markdown('<div style="font-size:12px;color:#8899AA;margin-bottom:10px;">Top Risk Profiles</div>', unsafe_allow_html=True)
    suggestions = search_customers(DB_PATH, "C", limit=5)
    
    if suggestions:
        cols = st.columns(len(suggestions))
        for i, s in enumerate(suggestions):
            with cols[i]:
                color = "#FF2D55" if s["risk_score_avg"] > 75 else "#FF8A00" if s["risk_score_avg"] > 50 else "#00E676"
                if st.button(f"{s['customer_id'][:12]}...", key=f"sug_{s['customer_id']}"):
                    st.session_state.selected_customer_id = s["customer_id"]
                    st.rerun()
                st.markdown(f'<div style="text-align:center;font-size:10px;color:{color};">{s["risk_score_avg"]:.1f} Avg Risk</div>', unsafe_allow_html=True)
    st.stop()

# Auto select if search has exact match
if "selected_customer_id" not in st.session_state:
    st.session_state.selected_customer_id = search_query

results = search_customers(DB_PATH, search_query)

if not results and search_query:
    st.warning(f"No customer found matching '{search_query}'")
    st.stop()
elif search_query != st.session_state.get("last_search"):
    st.session_state.last_search = search_query
    st.session_state.selected_customer_id = results[0]["customer_id"]

customer_id = st.session_state.selected_customer_id

if len(results) > 1:
    customer_id = st.selectbox("Select Customer from results:", [r["customer_id"] for r in results], 
                               index=[r["customer_id"] for r in results].index(customer_id) if customer_id in [r["customer_id"] for r in results] else 0)
    st.session_state.selected_customer_id = customer_id


# ── Customer Dashboard ────────────────────────────────────────────────────────
st.markdown("---")
with st.spinner("Compiling 360 profile..."):
    profile = get_or_create_customer_profile(DB_PATH, customer_id)
    log_audit_event(DB_PATH, user["username"], "Viewed Customer Profile", "customer", customer_id)

st.markdown(f"""
<div style="display:flex;align-items:center;gap:15px;margin-bottom:25px;">
    <div style="width:60px;height:60px;border-radius:50%;background:rgba(0,180,255,0.1);
                border:2px solid #00B4FF;display:flex;align-items:center;justify-content:center;
                font-size:24px;">👤</div>
    <div>
        <div style="font-size:24px;font-weight:800;color:#E8F0FF;font-family:DM Mono,monospace;">{profile['customer_id']}</div>
        <div style="font-size:12px;color:#8899AA;text-transform:uppercase;letter-spacing:0.1em;">
            First Seen: {str(profile.get('first_transaction_at', 'Unknown'))[:10]} | 
            Last Active: {str(profile.get('last_transaction_at', 'Unknown'))[:10]}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


c1, c2, c3, c4 = st.columns(4)
trend_color = "#FF2D55" if profile['risk_trend'] == "INCREASING" else "#00E676" if profile['risk_trend'] == "DECREASING" else "#8899AA"
avg_risk_color = "#FF2D55" if profile["risk_score_avg"] >= 80 else "#FF8A00" if profile["risk_score_avg"] >= 50 else "#00E676"

c1.markdown(f"""
<div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);border-radius:12px;padding:20px;">
    <div style="font-size:12px;color:#8899AA;text-transform:uppercase;">Avg Risk Score</div>
    <div style="font-size:32px;font-weight:800;color:{avg_risk_color};">{profile['risk_score_avg']:.1f}</div>
    <div style="font-size:11px;color:{trend_color};font-weight:700;">{profile['risk_trend']} TREND</div>
</div>
""", unsafe_allow_html=True)

c2.markdown(f"""
<div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);border-radius:12px;padding:20px;">
    <div style="font-size:12px;color:#8899AA;text-transform:uppercase;">Transactions</div>
    <div style="font-size:32px;font-weight:800;color:#E8F0FF;">{profile['total_transactions']}</div>
    <div style="font-size:11px;color:#FF2D55;font-weight:700;">{profile['fraud_count']} FLAGGED HIGH RISK</div>
</div>
""", unsafe_allow_html=True)

c3.markdown(f"""
<div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);border-radius:12px;padding:20px;">
    <div style="font-size:12px;color:#8899AA;text-transform:uppercase;">Avg Ticket Size</div>
    <div style="font-size:32px;font-weight:800;color:#E8F0FF;">₹{profile['avg_amount']:,.0f}</div>
    <div style="font-size:11px;color:#8899AA;">Max: ₹{profile['max_amount']:,.0f}</div>
</div>
""", unsafe_allow_html=True)

c4.markdown(f"""
<div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);border-radius:12px;padding:20px;">
    <div style="font-size:12px;color:#8899AA;text-transform:uppercase;">Device & Network Intel</div>
    <div style="display:flex;justify-content:space-between;margin-top:5px;">
        <div style="text-align:center;">
            <div style="font-size:24px;font-weight:800;color:#00B4FF;">{profile['device_count']}</div>
            <div style="font-size:10px;color:#8899AA;">DEVICES</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:24px;font-weight:800;color:#00B4FF;">{profile['country_count']}</div>
            <div style="font-size:10px;color:#8899AA;">LOCATIONS</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Recent Transactions Table ─────────────────────────────────────────────────
st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">Recent Activity for this Customer</div>', unsafe_allow_html=True)

import sqlite3
con = sqlite3.connect(DB_PATH, check_same_thread=False)
df = pd.read_sql_query(
    f"""
    SELECT id, created_at, ml_risk_level, final_risk_level, final_risk_score, status 
    FROM prediction_logs 
    WHERE transaction_json LIKE '%"{customer_id}"%'
    ORDER BY created_at DESC 
    LIMIT 20
    """, con
)
con.close()

if not df.empty:
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": "Log ID",
            "created_at": "Timestamp",
            "ml_risk_level": "Base Risk",
            "final_risk_level": "Final Risk",
            "final_risk_score": st.column_config.ProgressColumn("Risk Score", min_value=0, max_value=100),
            "status": "Operations Status"
        }
    )
else:
    st.info("No detailed logs found.")
