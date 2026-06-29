import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path
from src.export_manager import get_export_data, to_csv, to_excel, to_json
from src.auth import log_audit_event

st.set_page_config(page_title="Export Center", page_icon="📤", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="export_data")
user = st.session_state.user
DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

st.markdown('<div class="page-title">Compliance <span class="gradient-word">Export Center</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Securely extract data for regulatory reporting and offline analysis</div>', unsafe_allow_html=True)


# ── Configuration ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);
            border-radius:12px;padding:25px;margin-bottom:20px;">
    <div style="font-size:16px;font-weight:700;color:#E8F0FF;margin-bottom:20px;">Export Configuration</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    dataset = st.selectbox("Target Dataset", [
        "prediction_logs", "fraud_cases", "audit_logs", "customer_profiles"
    ])
    
    limit = st.slider("Record Limit", min_value=100, max_value=10000, value=1000, step=100)

with c2:
    status_filter = "All"
    risk_filter = "All"
    
    if dataset in ["prediction_logs", "fraud_cases"]:
        status_opts = ["All", "APPROVED", "PENDING_REVIEW", "BLOCKED"] if dataset == "prediction_logs" else ["All", "Open", "Investigating", "Escalated", "Resolved", "False_Positive"]
        status_filter = st.selectbox("Status Filter", status_opts)
        
    if dataset == "prediction_logs":
        risk_filter = st.selectbox("Risk Level", ["All", "LOW", "MEDIUM", "HIGH", "CRITICAL"])

st.markdown('</div>', unsafe_allow_html=True)


# ── Action Buttons ────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Generate Export</div>', unsafe_allow_html=True)

export_df = get_export_data(DB_PATH, dataset, status_filter, risk_filter, limit)
record_count = len(export_df)

if record_count == 0:
    st.warning("No records found matching the current criteria.")
else:
    st.markdown(f'<div style="font-size:14px;color:#8899AA;margin-bottom:20px;">Ready to export <b>{record_count}</b> records.</div>', unsafe_allow_html=True)
    
    col_csv, col_xlsx, col_json = st.columns(3)
    
    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    base_filename = f"fraud_export_{dataset}_{now_str}"
    
    with col_csv:
        csv_data = to_csv(export_df)
        if st.download_button(
            label="📄 Download as CSV",
            data=csv_data,
            file_name=f"{base_filename}.csv",
            mime="text/csv",
            use_container_width=True
        ):
            log_audit_event(DB_PATH, user["username"], f"Exported {dataset} (CSV)", "export", str(record_count))
            st.toast("CSV Export downloaded!")

    with col_xlsx:
        try:
            excel_data = to_excel(export_df)
            if st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"{base_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            ):
                log_audit_event(DB_PATH, user["username"], f"Exported {dataset} (Excel)", "export", str(record_count))
                st.toast("Excel Export downloaded!")
        except ImportError:
            st.error("Excel export requires 'openpyxl'. Run `pip install openpyxl`.")
            
    with col_json:
        json_data = to_json(export_df)
        if st.download_button(
            label="{} Download as JSON",
            data=json_data,
            file_name=f"{base_filename}.json",
            mime="application/json",
            use_container_width=True
        ):
            log_audit_event(DB_PATH, user["username"], f"Exported {dataset} (JSON)", "export", str(record_count))
            st.toast("JSON Export downloaded!")

    st.markdown("---")
    st.markdown('<div class="section-label">Data Preview</div>', unsafe_allow_html=True)
    st.dataframe(export_df.head(10), use_container_width=True)
