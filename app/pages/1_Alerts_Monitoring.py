import streamlit as st
import pandas as pd
import sqlite3
import requests
import html as html_lib
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils_dashboard import get_db_path, load_logs_df
from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile

st.set_page_config(page_title="Compliance Operations Console", page_icon="🚨", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_alerts")

# ════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    display_user_profile()

st.markdown("""
<div style="padding:1rem 0 1.5rem">
  <div class="page-title">
    Compliance <span class="gradient-word">Operations</span> Console
  </div>
  <div class="page-subtitle">
    Investigate and adjudicate flagged transactions
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="hdivider"></div>', unsafe_allow_html=True)

DB_PATH = get_db_path(PROJECT_ROOT)
df = load_logs_df(DB_PATH, limit=2000)

if df.empty:
    st.info("No logs found.")
    st.stop()

# ── FILTERS ────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([2,2,1.5,1.5])
with c1:
    f_status = st.multiselect("Review Status", ["PENDING_REVIEW", "APPROVED", "BLOCKED"], default=["PENDING_REVIEW"])
with c2:
    f_risk = st.multiselect("Risk Level", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH", "MEDIUM"])
with c3:
    f_override = st.checkbox("Policy Overrides Only", value=False)
with c4:
    if st.button("↻ Refresh Data", use_container_width=True):
        st.rerun()

# Apply filters
f_df = df.copy()
if f_status:
    f_df = f_df[f_df.get("status", pd.Series("PENDING_REVIEW", index=f_df.index)).isin(f_status)]
if f_risk:
    f_df = f_df[f_df["final_risk_level"].isin(f_risk)]
if f_override:
    f_df = f_df[f_df["policy_override_applied"] == 1]

if f_df.empty:
    st.success("No transactions match the current filters. Queue is clear!")
    st.stop()

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

# ── LAYOUT ────────────────────────────────────────────────────────
col_queue, col_detail = st.columns([1, 1.3])

# Helpers
def update_status(log_id, new_status):
    try:
        res = requests.post(f"http://localhost:8000/logs/{log_id}/action", json={"status": new_status}, timeout=2)
        if res.status_code != 200:
            # Fallback to direct DB
            raise Exception("API failed")
    except:
        con = sqlite3.connect(DB_PATH)
        con.execute("UPDATE prediction_logs SET status = ? WHERE id = ?", (new_status, int(log_id)))
        con.commit()
        con.close()
    st.rerun()

with col_queue:
    st.markdown('<div class="section-label">Action Queue</div>', unsafe_allow_html=True)
    
    # We will build a custom list or use dataframe selection
    # For a premium feel, let's use a custom HTML list with Streamlit buttons next to it,
    # or just use st.selectbox for selection.
    
    queue_ids = f_df["id"].tolist()
    if "selected_log_id" not in st.session_state or st.session_state.selected_log_id not in queue_ids:
        st.session_state.selected_log_id = queue_ids[0]
        
    selected_id = st.selectbox("Select Transaction ID to investigate:", queue_ids, 
                               index=queue_ids.index(st.session_state.selected_log_id))
    st.session_state.selected_log_id = selected_id
    
    # Show summary of queue
    st.markdown(f'<div style="font-size:12px;color:#5A8AA8;margin-top:-10px;margin-bottom:20px;">Showing {len(f_df)} transactions</div>', unsafe_allow_html=True)
    
    # Queue preview table
    preview_df = f_df[["id", "created_at", "final_risk_level", "final_risk_score", "status"]].head(15).copy()
    preview_df["created_at"] = preview_df["created_at"].dt.strftime("%m-%d %H:%M")
    st.dataframe(preview_df, use_container_width=True, hide_index=True)


with col_detail:
    st.markdown('<div class="section-label">Investigation Details</div>', unsafe_allow_html=True)
    row = f_df[f_df["id"] == selected_id].iloc[0]
    
    risk_col = {"CRITICAL":"#FF2D55","HIGH":"#FF8A00","MEDIUM":"#FFB800","LOW":"#00E5A0"}.get(row["final_risk_level"], "#8899AA")
    status_col = {"APPROVED":"#00E5A0", "PENDING_REVIEW":"#FF8A00", "BLOCKED":"#FF2D55"}.get(row.get("status","PENDING_REVIEW"), "#8899AA")
    
    st.markdown(f"""
    <div style="background:rgba(8,13,26,0.8);border:1px solid rgba(148,163,184,0.1);
                border-radius:12px;padding:20px;margin-bottom:20px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
            <div>
                <span style="font-size:12px;color:#5A8AA8;text-transform:uppercase;letter-spacing:0.1em;">Transaction ID</span>
                <div style="font-size:24px;font-family:DM Mono,monospace;font-weight:700;color:#E8F0FF;">{row['id']}</div>
            </div>
            <div style="text-align:right;">
                <span style="font-size:12px;color:#5A8AA8;text-transform:uppercase;letter-spacing:0.1em;">Status</span>
                <div style="font-size:16px;font-weight:700;color:{status_col};">{row.get("status", "PENDING_REVIEW")}</div>
            </div>
        </div>
        
        <div style="display:flex;gap:30px;">
            <div>
                <span style="font-size:10px;color:#5A8AA8;text-transform:uppercase;letter-spacing:0.1em;">Final Risk</span>
                <div style="font-size:18px;font-weight:700;color:{risk_col};">{row['final_risk_level']} ({row['final_risk_score']})</div>
            </div>
            <div>
                <span style="font-size:10px;color:#5A8AA8;text-transform:uppercase;letter-spacing:0.1em;">ML Base Risk</span>
                <div style="font-size:18px;font-weight:600;color:#8899AA;">{row['ml_risk_level']} ({row.get('ml_risk_score',0)})</div>
            </div>
            <div>
                <span style="font-size:10px;color:#5A8AA8;text-transform:uppercase;letter-spacing:0.1em;">Policy Override</span>
                <div style="font-size:18px;font-weight:600;color:{'#A855F7' if row['policy_override_applied'] else '#8899AA'};">
                    {'YES' if row['policy_override_applied'] else 'NO'}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("✅ Approve Transaction", type="primary", use_container_width=True):
            update_status(selected_id, "APPROVED")
    with bc2:
        if st.button("🚫 Block Transaction", use_container_width=True):
            update_status(selected_id, "BLOCKED")
            
    st.markdown("---")
    
    st.markdown('<div class="section-label">Fraud Indicators (SHAP Approx)</div>', unsafe_allow_html=True)
    # Fake SHAP for demo: highlight high amount, balance discrepancies
    tx = row["transaction"] if isinstance(row["transaction"], dict) else json.loads(row["transaction"]) if isinstance(row["transaction"], str) else {}
    
    features_html = ""
    for k, v in tx.items():
        if k in ["step", "isFraud", "isFlaggedFraud", "nameOrig", "nameDest"]: continue
        
        # Color hack for demo
        val_str = str(v)
        color = "#8899AA"
        if isinstance(v, (int, float)):
            if k == "amount" and v > 50000: color = "#FF8A00"
            if k.startswith("old") or k.startswith("new"): val_str = f"₹{v:,.2f}"
            if k == "amount": val_str = f"₹{v:,.2f}"
            
        features_html += f"""
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(148,163,184,0.05);">
            <span style="font-size:12px;color:#5A8AA8;">{k}</span>
            <span style="font-size:13px;font-family:DM Mono,monospace;font-weight:600;color:{color};">{val_str}</span>
        </div>
        """
        
    st.markdown(f'<div style="background:rgba(8,13,26,0.5);border:1px solid rgba(148,163,184,0.1);padding:15px;border-radius:10px;">{features_html}</div>', unsafe_allow_html=True)
    
    if row["policy_override_applied"]:
        st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Policy Reasons Triggered</div>', unsafe_allow_html=True)
        reasons = row["policy_reasons"] if isinstance(row["policy_reasons"], list) else json.loads(row["policy_reasons"]) if isinstance(row["policy_reasons"], str) else []
        for r in reasons:
            st.error(f"🚨 {r}")