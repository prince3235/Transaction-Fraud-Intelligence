import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path
from src.case_manager import (
    list_cases, get_case_stats, update_case_status,
    add_note, assign_case, VALID_STATUSES, VALID_PRIORITIES
)
from src.auth import log_audit_event

st.set_page_config(page_title="Case Management", page_icon="📁", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_cases")
user = st.session_state.user

DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Case <span class="gradient-word">Management</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Track and resolve fraud investigations</div>', unsafe_allow_html=True)


# ── Stats Row ─────────────────────────────────────────────────────────────────
stats = get_case_stats(DB_PATH)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Cases</div>
        <div class="metric-value">{stats['total']}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Open / Investigating</div>
        <div class="metric-value">{stats['open'] + stats['investigating']}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label" style="color:#FF2D55;">Escalated</div>
        <div class="metric-value" style="color:#FF2D55;">{stats['escalated']}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label" style="color:#00E676;">Resolved</div>
        <div class="metric-value" style="color:#00E676;">{stats['resolved']}</div>
    </div>
    """, unsafe_allow_html=True)


st.markdown("---")


# ── Main UI (Split pane) ──────────────────────────────────────────────────────
# Left pane: Case Queue
# Right pane: Case Detail (if selected)

if "selected_case" not in st.session_state:
    st.session_state.selected_case = None

c1, c2 = st.columns([1, 1.5])

with c1:
    st.markdown('<div class="section-label">Case Queue</div>', unsafe_allow_html=True)
    
    # Filters
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        f_status = st.selectbox("Status", ["All"] + list(VALID_STATUSES))
    with f_col2:
        f_priority = st.selectbox("Priority", ["All"] + list(VALID_PRIORITIES))
        
    f_search = st.text_input("Search (ID, Title, Desc)")
    
    kwargs = {}
    if f_status != "All": kwargs["status"] = f_status
    if f_priority != "All": kwargs["priority"] = f_priority
    if f_search: kwargs["search"] = f_search
    
    cases = list_cases(DB_PATH, **kwargs)
    
    st.markdown(f"<div style='font-size:12px;color:#8899AA;margin-bottom:10px;'>Showing {len(cases)} cases</div>", unsafe_allow_html=True)
    
    for case in cases:
        status_color = "#8899AA"
        if case["status"] == "Open": status_color = "#00B4FF"
        elif case["status"] == "Investigating": status_color = "#FF8A00"
        elif case["status"] == "Escalated": status_color = "#FF2D55"
        elif case["status"] in ("Resolved", "False_Positive"): status_color = "#00E676"
        
        pri_color = "#8899AA"
        if case["priority"] == "Critical": pri_color = "#FF2D55"
        elif case["priority"] == "High": pri_color = "#FF8A00"
        
        selected_style = ""
        if st.session_state.selected_case and st.session_state.selected_case["id"] == case["id"]:
            selected_style = "border-color: #00B4FF; background: rgba(0,180,255,0.05);"
            
        st.markdown(f"""
        <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);
                    border-radius:8px;padding:15px;margin-bottom:10px;cursor:pointer;{selected_style}">
            <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                <span style="font-weight:700;color:#E8F0FF;font-size:14px;">{case['case_id']}</span>
                <span style="color:{status_color};font-size:11px;font-weight:700;border:1px solid {status_color}44;padding:2px 6px;border-radius:4px;">{case['status']}</span>
            </div>
            <div style="font-size:13px;color:#BAC4D0;margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {case['title']}
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:#8899AA;">
                <span>Pri: <strong style="color:{pri_color}">{case['priority']}</strong></span>
                <span>Assigned: <strong>{case['assigned_to'] or 'Unassigned'}</strong></span>
                <span>{case['created_at'][:10]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("View Details", key=f"btn_{case['id']}", use_container_width=True):
            st.session_state.selected_case = case
            st.rerun()


with c2:
    st.markdown('<div class="section-label">Case Details</div>', unsafe_allow_html=True)
    
    case = st.session_state.selected_case
    if not case:
        st.info("Select a case from the queue to view details.")
    else:
        st.markdown(f"""
        <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);
                    border-radius:12px;padding:25px;margin-bottom:20px;">
            <div style="font-size:12px;color:#00B4FF;font-weight:700;margin-bottom:5px;">{case['case_id']}</div>
            <div style="font-size:22px;font-weight:800;color:#E8F0FF;margin-bottom:15px;">{case['title']}</div>
            <div style="font-size:14px;color:#BAC4D0;line-height:1.5;margin-bottom:20px;">
                {case['description']}
            </div>
            
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px;
                        background:rgba(0,0,0,0.2);padding:15px;border-radius:8px;">
                <div>
                    <div style="font-size:11px;color:#8899AA;text-transform:uppercase;">Priority</div>
                    <div style="font-size:14px;font-weight:700;color:#E8F0FF;">{case['priority']}</div>
                </div>
                <div>
                    <div style="font-size:11px;color:#8899AA;text-transform:uppercase;">Status</div>
                    <div style="font-size:14px;font-weight:700;color:#E8F0FF;">{case['status']}</div>
                </div>
                <div>
                    <div style="font-size:11px;color:#8899AA;text-transform:uppercase;">Assigned To</div>
                    <div style="font-size:14px;font-weight:700;color:#E8F0FF;">{case['assigned_to'] or 'Unassigned'}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Actions Tab
        t1, t2, t3 = st.tabs(["📝 Notes", "⏳ Timeline", "⚙️ Actions"])
        
        with t1:
            for note in case.get("notes", []):
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(148,163,184,0.05);
                            border-radius:8px;padding:15px;margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:12px;">
                        <span style="font-weight:700;color:#00B4FF;">@{note['author']}</span>
                        <span style="color:#8899AA;">{note['timestamp'][:16].replace('T', ' ')}</span>
                    </div>
                    <div style="font-size:13px;color:#E8F0FF;">{note['content']}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with st.form(f"note_form_{case['id']}"):
                new_note = st.text_area("Add Investigation Note")
                if st.form_submit_button("Post Note"):
                    if new_note.strip():
                        updated_case = add_note(DB_PATH, case["case_id"], user["username"], new_note.strip())
                        log_audit_event(DB_PATH, user["username"], "Note Added", "fraud_case", case["case_id"])
                        st.session_state.selected_case = updated_case
                        st.rerun()
                        
        with t2:
            timeline_html = "<div style='margin-left:20px;border-left:2px solid #00B4FF;padding-left:20px;'>"
            for event in reversed(case.get("timeline", [])):
                timeline_html += f"""
                <div style="position:relative;margin-bottom:20px;">
                    <div style="position:absolute;left:-26px;top:0;width:10px;height:10px;
                                border-radius:50%;background:#00B4FF;"></div>
                    <div style="font-size:12px;color:#8899AA;">{event['timestamp'][:16].replace('T', ' ')} • <b>@{event['actor']}</b></div>
                    <div style="font-size:14px;font-weight:700;color:#E8F0FF;margin:4px 0;">{event['action']}</div>
                    <div style="font-size:13px;color:#BAC4D0;">{event.get('note', '')}</div>
                </div>
                """
            timeline_html += "</div>"
            st.markdown(timeline_html, unsafe_allow_html=True)
            
        with t3:
            st.markdown("#### Update Status")
            new_status = st.selectbox("Status", list(VALID_STATUSES), index=list(VALID_STATUSES).index(case['status']))
            reason = st.text_input("Reason for change (optional)")
            if st.button("Update Case Status", type="primary"):
                if new_status != case['status']:
                    updated = update_case_status(DB_PATH, case['case_id'], new_status, user['username'], reason)
                    log_audit_event(DB_PATH, user["username"], "Case Status Updated", "fraud_case", case["case_id"], case['status'], new_status)
                    st.session_state.selected_case = updated
                    st.success(f"Status updated to {new_status}")
                    st.rerun()
                    
            st.markdown("#### Reassign Case")
            new_assignee = st.text_input("Assign to (username)", value=case['assigned_to'] or "")
            if st.button("Assign"):
                if new_assignee != case['assigned_to']:
                    updated = assign_case(DB_PATH, case['case_id'], new_assignee, user['username'])
                    log_audit_event(DB_PATH, user["username"], "Case Assigned", "fraud_case", case["case_id"], case['assigned_to'], new_assignee)
                    st.session_state.selected_case = updated
                    st.success(f"Assigned to {new_assignee}")
                    st.rerun()
