import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path
from src.model_registry import list_model_versions, promote_model, archive_model
from src.auth import log_audit_event, has_permission
import pandas as pd

st.set_page_config(page_title="Model Registry", page_icon="📦", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_model")
user = st.session_state.user

DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Model <span class="gradient-word">Registry</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Track, compare, and promote ML model versions</div>', unsafe_allow_html=True)


show_archived = st.checkbox("Show archived versions", value=False)
versions = list_model_versions(DB_PATH, include_archived=show_archived)

if not versions:
    st.info("No models found in the registry.")
    st.stop()

# ── Active Model Highlight ────────────────────────────────────────────────────
active_model = next((v for v in versions if v["is_production"]), None)
if active_model:
    st.markdown(f"""
    <div style="background:rgba(0,180,255,0.05);border:1px solid rgba(0,180,255,0.2);
                border-left:4px solid #00B4FF;border-radius:12px;padding:20px;margin-bottom:30px;">
        <div style="font-size:12px;color:#00B4FF;font-weight:700;text-transform:uppercase;margin-bottom:4px;">
            Active Production Model
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <span style="font-size:24px;font-weight:800;color:#E8F0FF;margin-right:15px;">{active_model['version']}</span>
                <span style="font-size:14px;color:#BAC4D0;">Deployed on {active_model['created_at'][:10]}</span>
            </div>
            <div style="display:flex;gap:20px;">
                <div style="text-align:right;">
                    <div style="font-size:11px;color:#8899AA;">ROC AUC</div>
                    <div style="font-size:16px;font-weight:700;color:#00E676;">{active_model['roc_auc']:.4f}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:11px;color:#8899AA;">PR AUC</div>
                    <div style="font-size:16px;font-weight:700;color:#00E676;">{active_model['pr_auc']:.4f}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Version History Table ─────────────────────────────────────────────────────
st.markdown('<div class="section-label">Version History</div>', unsafe_allow_html=True)

df = pd.DataFrame(versions)
df["status"] = df.apply(lambda r: "🟢 Production" if r["is_production"] else ("🗄️ Archived" if r["is_archived"] else "⚪ Inactive"), axis=1)

display_df = df[["version", "status", "roc_auc", "pr_auc", "f1_val", "dataset_size", "training_date", "notes"]]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "version": "Version",
        "status": "Status",
        "roc_auc": st.column_config.NumberColumn("ROC AUC", format="%.4f"),
        "pr_auc": st.column_config.NumberColumn("PR AUC", format="%.4f"),
        "f1_val": st.column_config.NumberColumn("F1 Score", format="%.4f"),
        "dataset_size": "Training Size",
        "training_date": "Date",
        "notes": "Notes",
    }
)

# ── Management Actions ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-label">Management Actions</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    with st.form("promote_form"):
        st.markdown("#### Promote to Production")
        st.caption("Change the active model used by the API.")
        inactive_versions = [v["version"] for v in versions if not v["is_production"] and not v["is_archived"]]
        selected_version = st.selectbox("Select Version", inactive_versions)
        
        if st.form_submit_button("🚀 Deploy to Production", type="primary") and selected_version:
            if has_permission(user["role"], "retrain_model"):
                promote_model(DB_PATH, selected_version)
                log_audit_event(DB_PATH, user["username"], "Model Promoted", "model_registry", selected_version)
                st.success(f"{selected_version} is now the active production model.")
                st.rerun()
            else:
                st.error("Access Denied: Requires 'retrain_model' permission.")

with c2:
    with st.form("archive_form"):
        st.markdown("#### Archive Model")
        st.caption("Hide older versions from the active list.")
        # Can't archive production model
        archivable_versions = [v["version"] for v in versions if not v["is_production"] and not v["is_archived"]]
        to_archive = st.selectbox("Select Version to Archive", archivable_versions)
        
        if st.form_submit_button("🗄️ Archive Version") and to_archive:
            if has_permission(user["role"], "retrain_model"):
                archive_model(DB_PATH, to_archive)
                log_audit_event(DB_PATH, user["username"], "Model Archived", "model_registry", to_archive)
                st.success(f"{to_archive} archived.")
                st.rerun()
            else:
                st.error("Access Denied: Requires 'retrain_model' permission.")
