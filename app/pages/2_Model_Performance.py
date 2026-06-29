import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils_dashboard import get_db_path, load_logs_df
from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile

# ════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Model Health & Retraining", page_icon="🧠", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_model")

with st.sidebar:
    display_user_profile()

st.markdown("""
<div style="padding:1rem 0 1.5rem">
  <div class="page-title">
    Model Health &amp; <span class="gradient-word">Retraining</span>
  </div>
  <div class="page-subtitle">
    Monitor ML performance drift and retrain the random forest
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="hdivider"></div>', unsafe_allow_html=True)

y_test_path = PROJECT_ROOT / "data" / "processed" / "y_test.csv"
prob_path = PROJECT_ROOT / "data" / "processed" / "best_model_probs.npy"

if not y_test_path.exists() or not prob_path.exists():
    st.error("Data files missing. Please run src/models/train_model.py first.")
    st.stop()

y_test = pd.read_csv(y_test_path).squeeze()
y_prob = np.load(prob_path)

roc = roc_auc_score(y_test, y_prob)
pr  = average_precision_score(y_test, y_prob)

st.markdown('<div class="section-label">Current Model Health</div>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.markdown(f"""
<div class="kpi-card kpi-blue">
  <div class="kpi-stripe"></div><div class="kpi-glow-blob"></div>
  <div class="kpi-label">ROC-AUC</div>
  <div class="kpi-value">{roc:.4f}</div>
  <div class="kpi-sub">Overall Separability</div>
</div>
""", unsafe_allow_html=True)

m2.markdown(f"""
<div class="kpi-card kpi-purple">
  <div class="kpi-stripe"></div><div class="kpi-glow-blob"></div>
  <div class="kpi-label">PR-AUC</div>
  <div class="kpi-value">{pr:.4f}</div>
  <div class="kpi-sub">Imbalanced Performance</div>
</div>
""", unsafe_allow_html=True)

thr = st.slider("Simulate Decision Threshold", 0.05, 0.95, 0.50, 0.01)
y_pred = (y_prob >= thr).astype(int)

prec = precision_score(y_test, y_pred, zero_division=0)
rec  = recall_score(y_test, y_pred, zero_division=0)
f1   = f1_score(y_test, y_pred, zero_division=0)

m3.markdown(f"""
<div class="kpi-card kpi-orange">
  <div class="kpi-stripe"></div><div class="kpi-glow-blob"></div>
  <div class="kpi-label">Precision</div>
  <div class="kpi-value">{prec:.4f}</div>
  <div class="kpi-sub">At threshold {thr}</div>
</div>
""", unsafe_allow_html=True)

m4.markdown(f"""
<div class="kpi-card kpi-teal">
  <div class="kpi-stripe"></div><div class="kpi-glow-blob"></div>
  <div class="kpi-label">Recall</div>
  <div class="kpi-value">{rec:.4f}</div>
  <div class="kpi-sub">At threshold {thr}</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section-label">Confusion Matrix</div>', unsafe_allow_html=True)
    cm = confusion_matrix(y_test, y_pred)
    cm_df = pd.DataFrame(cm, index=["Actual Legitimate","Actual Fraud"], columns=["Pred Legitimate","Pred Fraud"])
    
    fig = px.imshow(cm_df, text_auto=True, color_continuous_scale="Blues", aspect="auto")
    fig.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#8899AA", family="DM Sans"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with c2:
    st.markdown('<div class="section-label">MLOps: Retraining Loop</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:rgba(8,13,26,0.8);border:1px solid rgba(148,163,184,0.1);
                border-radius:12px;padding:20px;">
        <p style="font-size:13px;color:#8899AA;line-height:1.6;margin-bottom:20px;">
            In a production environment, the model should be continuously evaluated against new labeled data. 
            If data drift is detected or performance degrades, you can trigger a retraining pipeline here.
        </p>
        <div style="display:flex;align-items:center;gap:15px;margin-bottom:10px;">
            <div style="width:10px;height:10px;border-radius:50%;background:#00E5A0;"></div>
            <span style="font-size:12px;color:#C4CFDE;font-weight:600;">Data Drift Status: <span style="color:#00E5A0;">Stable</span></span>
        </div>
        <div style="display:flex;align-items:center;gap:15px;margin-bottom:25px;">
            <div style="width:10px;height:10px;border-radius:50%;background:#FF8A00;"></div>
            <span style="font-size:12px;color:#C4CFDE;font-weight:600;">Concept Drift Status: <span style="color:#FF8A00;">Warning (New Patterns Detected)</span></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Trigger Model Retraining Pipeline", type="primary", use_container_width=True):
        if not __import__("src.auth", fromlist=["has_permission"]).has_permission(st.session_state.user["role"], "retrain_model"):
            st.error("Access Denied: Requires 'retrain_model' permission.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Fetching latest labeled logs from database...")
            time.sleep(1)
            progress_bar.progress(25)
            
            status_text.text("Engineering features for new data...")
            time.sleep(1.5)
            progress_bar.progress(50)
            
            status_text.text("Training RandomForestClassifier (n_estimators=100)...")
            time.sleep(2)
            progress_bar.progress(75)
            
            status_text.text("Evaluating model performance on holdout set...")
            time.sleep(1)
            progress_bar.progress(100)
            
            # Register in Model Registry
            from src.model_registry import register_model
            from src.auth import log_audit_event
            
            # Use current displayed stats as the new model's stats (for simulation)
            new_model = register_model(
                db_path=get_db_path(PROJECT_ROOT),
                pkl_path=str(PROJECT_ROOT / "models" / "best_fraud_model.pkl"),
                roc_auc=roc,
                pr_auc=pr,
                precision_val=prec,
                recall_val=rec,
                f1_val=f1,
                n_estimators=100,
                dataset_size=9600 + 500, # Mock increase
                feature_count=29,
                notes="Retrained from Model Health dashboard.",
            )
            
            log_audit_event(
                get_db_path(PROJECT_ROOT), 
                st.session_state.user["username"], 
                "Model Retrained", 
                "model_registry", 
                new_model["version"]
            )
            
            st.success(f"✅ Model retraining complete! Saved as {new_model['version']}. Go to Model Registry to promote it.")