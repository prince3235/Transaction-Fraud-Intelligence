import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path
from src.rules_engine import list_rules, toggle_rule, create_rule, RULE_TYPES, RISK_BUMPS
from src.auth import log_audit_event
import json

st.set_page_config(page_title="Rules Engine", page_icon="⚙️", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="manage_rules")
user = st.session_state.user

DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Business <span class="gradient-word">Rules Engine</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Configure heuristic policies that override or enhance ML predictions</div>', unsafe_allow_html=True)

# ── Rules List ────────────────────────────────────────────────────────────────
rules = list_rules(DB_PATH)
active_count = sum(1 for r in rules if r["is_active"])

c1, c2 = st.columns([3, 1])
with c1:
    st.markdown(f'<div class="section-label">Active Rules ({active_count}/{len(rules)})</div>', unsafe_allow_html=True)
with c2:
    if st.button("➕ Create New Rule", type="primary", use_container_width=True):
        st.session_state.show_rule_form = True

for rule in rules:
    status_color = "#00E676" if rule["is_active"] else "#FF2D55"
    status_text = "ACTIVE" if rule["is_active"] else "DISABLED"
    opacity = "1.0" if rule["is_active"] else "0.5"
    
    with st.container():
        st.markdown(f"""
        <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);
                    border-radius:12px;padding:20px;margin-bottom:15px;opacity:{opacity};
                    border-left:4px solid {status_color};">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div style="font-size:18px;font-weight:800;color:#E8F0FF;margin-bottom:5px;">
                        {rule['name']}
                    </div>
                    <div style="font-size:13px;color:#BAC4D0;margin-bottom:15px;">
                        {rule['description']}
                    </div>
                    <div style="display:flex;gap:15px;font-size:12px;">
                        <div style="background:rgba(255,255,255,0.05);padding:4px 10px;border-radius:4px;">
                            <span style="color:#8899AA;">Type:</span> <span style="color:#E8F0FF;font-weight:700;">{rule['rule_type']}</span>
                        </div>
                        <div style="background:rgba(255,255,255,0.05);padding:4px 10px;border-radius:4px;">
                            <span style="color:#8899AA;">Action:</span> <span style="color:#E8F0FF;font-weight:700;">{rule['action']} to {rule['risk_level_bump']}</span>
                        </div>
                        <div style="background:rgba(255,255,255,0.05);padding:4px 10px;border-radius:4px;">
                            <span style="color:#8899AA;">Priority:</span> <span style="color:#00B4FF;font-weight:700;">{rule['priority']}</span>
                        </div>
                        <div style="background:rgba(255,255,255,0.05);padding:4px 10px;border-radius:4px;">
                            <span style="color:#8899AA;">Triggered:</span> <span style="color:#FF8A00;font-weight:700;">{rule['triggered_count']} times</span>
                        </div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:11px;font-weight:800;color:{status_color};
                                border:1px solid {status_color}44;padding:4px 12px;
                                border-radius:100px;display:inline-block;margin-bottom:10px;">
                        {status_text}
                    </div>
                </div>
            </div>
            
            <div style="margin-top:15px;background:rgba(0,0,0,0.3);padding:10px;border-radius:6px;
                        font-family:monospace;font-size:12px;color:#00B4FF;">
                {rule['condition_json']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Toggle button
        col1, _ = st.columns([1, 5])
        with col1:
            toggle_label = "Disable Rule" if rule["is_active"] else "Enable Rule"
            if st.button(toggle_label, key=f"tgl_{rule['id']}", use_container_width=True):
                new_state = not rule["is_active"]
                toggle_rule(DB_PATH, rule["id"], new_state)
                log_audit_event(DB_PATH, user["username"], "Rule Toggled", "business_rule", str(rule["id"]), rule["is_active"], new_state)
                st.rerun()

# ── Create Rule Modal / Form ──────────────────────────────────────────────────
if st.session_state.get("show_rule_form", False):
    st.markdown("---")
    st.markdown('<div class="section-label">Create New Business Rule</div>', unsafe_allow_html=True)
    
    with st.form("new_rule_form"):
        r_name = st.text_input("Rule Name", placeholder="e.g., Impossible Travel Pattern")
        r_desc = st.text_input("Description", placeholder="e.g., Flags transactions spanning multiple countries in 1 hour")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            r_type = st.selectbox("Rule Type", RULE_TYPES)
        with c2:
            r_action = st.selectbox("Action", ["flag", "escalate", "block"])
        with c3:
            r_bump = st.selectbox("Risk Level Bump", RISK_BUMPS)
            
        r_priority = st.slider("Priority (100 = Highest)", min_value=1, max_value=100, value=50)
        
        r_cond = st.text_area("Condition JSON", value='{"field": "amount", "operator": ">", "threshold": 100000}')
        
        submitted = st.form_submit_button("💾 Save Rule", type="primary")
        if submitted:
            try:
                cond_dict = json.loads(r_cond)
                if not r_name.strip():
                    st.error("Rule name is required.")
                else:
                    create_rule(DB_PATH, r_name, r_desc, r_type, cond_dict, r_action, r_bump, r_priority)
                    log_audit_event(DB_PATH, user["username"], "Rule Created", "business_rule", r_name)
                    st.success("Rule created successfully!")
                    st.session_state.show_rule_form = False
                    st.rerun()
            except json.JSONDecodeError:
                st.error("Invalid JSON in condition field.")
    
    if st.button("Cancel"):
        st.session_state.show_rule_form = False
        st.rerun()
