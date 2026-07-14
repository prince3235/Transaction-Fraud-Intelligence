import streamlit as st
import sys
import html as html_lib
import json
from pathlib import Path
import sqlite3
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path
from src.auth import fetch_audit_logs, log_audit_event


def _safe_render(value) -> str:
    """HTML-safe string rendering for any value coming from the DB."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, indent=2, default=str)
        except (TypeError, ValueError):
            value = str(value)
    else:
        value = str(value)
    return html_lib.escape(value, quote=True)

st.set_page_config(page_title="Audit Logs", page_icon="📜", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_audit")
user = st.session_state.user
DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

st.markdown('<div class="page-title">Enterprise <span class="gradient-word">Audit Logs</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Immutable trail of all user actions and system changes</div>', unsafe_allow_html=True)


# ── Filters ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Filter Logs</div>', unsafe_allow_html=True)

f1, f2, f3 = st.columns(3)
with f1:
    f_user = st.text_input("Username (exact match)", placeholder="Leave blank for all")
with f2:
    f_entity = st.selectbox("Entity Type", ["All", "auth", "fraud_case", "business_rule", "prediction_log", "model_registry", "drift_snapshots", "export"])
with f3:
    f_limit = st.selectbox("Show latest", [50, 100, 500, 1000])
    
if f_entity == "All": f_entity = None
if not f_user.strip(): f_user = None

# ── Load Data ─────────────────────────────────────────────────────────────────
logs = fetch_audit_logs(DB_PATH, username=f_user, entity_type=f_entity, limit=f_limit)

if not logs:
    st.info("No audit logs found matching the criteria.")
    st.stop()
    
# ── Render Logs ───────────────────────────────────────────────────────────────
st.markdown(f'<div style="font-size:12px;color:#8899AA;margin-bottom:10px;">Showing latest {len(logs)} entries</div>', unsafe_allow_html=True)

for log in logs:
    action_color = "#00B4FF"
    if "Created" in log["action"] or "Approved" in log["action"]: action_color = "#00E676"
    elif "Deleted" in log["action"] or "Blocked" in log["action"] or "Failed" in log["action"]: action_color = "#FF2D55"
    elif "Updated" in log["action"] or "Toggled" in log["action"]: action_color = "#FF8A00"
    
    entity = f"{log['entity_type']} ({log['entity_id']})" if log['entity_id'] else str(log['entity_type'])
    entity = html_lib.escape(str(entity), quote=True)
    username = html_lib.escape(str(log['username']), quote=True)
    action_rendered = html_lib.escape(str(log['action']), quote=True)
    ip_rendered = html_lib.escape(str(log['ip_address']), quote=True)
    reason_rendered = html_lib.escape(str(log.get('reason') or ''), quote=True)
    
    with st.expander(f"{log['timestamp'][:19].replace('T', ' ')} — {log['username']} : {log['action']} ({entity})"):
        st.markdown(f"""
        <div style="background:rgba(0,0,0,0.2);padding:15px;border-radius:8px;font-family:DM Mono,monospace;font-size:12px;color:#BAC4D0;">
            <div style="margin-bottom:5px;"><span style="color:#8899AA;">Actor:</span> {username} (IP: {ip_rendered})</div>
            <div style="margin-bottom:5px;"><span style="color:#8899AA;">Action:</span> <span style="color:{action_color};font-weight:700;">{action_rendered}</span></div>
            <div style="margin-bottom:5px;"><span style="color:#8899AA;">Entity:</span> {entity}</div>
        """, unsafe_allow_html=True)
        
        if log.get("old_value_json") or log.get("new_value_json"):
            st.markdown('<div style="margin-top:10px;border-top:1px solid rgba(255,255,255,0.1);padding-top:10px;display:flex;gap:20px;">', unsafe_allow_html=True)
            
            if log.get("old_value_json"):
                st.markdown(f"""
                <div style="flex:1;">
                    <div style="color:#FF2D55;margin-bottom:5px;">Previous Value</div>
                    <div style="background:rgba(255,45,85,0.05);padding:10px;border-radius:4px;word-break:break-all;">{_safe_render(log['old_value_json'])}</div>
                </div>
                """, unsafe_allow_html=True)
                
            if log.get("new_value_json"):
                st.markdown(f"""
                <div style="flex:1;">
                    <div style="color:#00E676;margin-bottom:5px;">New Value</div>
                    <div style="background:rgba(0,230,118,0.05);padding:10px;border-radius:4px;word-break:break-all;">{_safe_render(log['new_value_json'])}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)
            
        if log.get("reason"):
            st.markdown(f'<div style="margin-top:10px;color:#FF8A00;">Reason: {reason_rendered}</div>', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
