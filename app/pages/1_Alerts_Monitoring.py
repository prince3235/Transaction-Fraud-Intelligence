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
from app.premium_design import inject_premium_design, section_header, render_detail_card
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
  <div class="page-title">Compliance Operations Console</div>
  <div class="page-subtitle">Investigate and adjudicate flagged transactions</div>
</div>
""", unsafe_allow_html=True)
st.markdown('<hr style="border-color:var(--border);">', unsafe_allow_html=True)

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
    st.markdown('<div style="height:32px"></div>', unsafe_allow_html=True)
    f_override = st.checkbox("Policy Overrides Only", value=False)
with c4:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
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

st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

# ── LAYOUT ────────────────────────────────────────────────────────
col_queue, col_detail = st.columns([1, 1.3])

def update_status(log_id, new_status):
    try:
        res = requests.post(f"http://localhost:8000/logs/{log_id}/action", json={"status": new_status}, timeout=2)
        if res.status_code != 200:
            raise Exception("API failed")
    except:
        con = sqlite3.connect(DB_PATH)
        con.execute("UPDATE prediction_logs SET status = ? WHERE id = ?", (new_status, int(log_id)))
        con.commit()
        con.close()
    st.rerun()

with col_queue:
    st.markdown(section_header("Action Queue"), unsafe_allow_html=True)
    
    queue_ids = f_df["id"].tolist()
    if "selected_log_id" not in st.session_state or st.session_state.selected_log_id not in queue_ids:
        st.session_state.selected_log_id = queue_ids[0]
        
    selected_id = st.selectbox("Select Transaction ID to investigate:", queue_ids, 
                               index=queue_ids.index(st.session_state.selected_log_id))
    st.session_state.selected_log_id = selected_id
    
    st.markdown(f'<div style="font-size:12px;color:var(--text-secondary);margin-top:-10px;margin-bottom:20px;">Showing {len(f_df)} transactions</div>', unsafe_allow_html=True)
    
    # Queue preview table
    cols = ["id", "created_at", "final_risk_level", "final_risk_score"]
    if "status" in f_df.columns: cols.append("status")
    preview_df = f_df[cols].head(15).copy()
    preview_df["created_at"] = preview_df["created_at"].dt.strftime("%m-%d %H:%M")
    st.dataframe(preview_df, use_container_width=True, hide_index=True)


with col_detail:
    st.markdown(section_header("Investigation Details"), unsafe_allow_html=True)
    row = f_df[f_df["id"] == selected_id].iloc[0]
    
    # CRITICAL BUG FIX: use render_detail_card helper to avoid raw HTML bleeding
    detail_data = {
        "ID": row['id'],
        "Timestamp": row['created_at'].strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(row['created_at']) else "N/A",
        "Status": row.get("status", "PENDING_REVIEW"),
        "Risk": row['final_risk_level'],
        "Risk Score": int(row['final_risk_score']),
        "ML Base Risk": f"{row['ml_risk_level']} ({row.get('ml_risk_score',0)})",
        "Policy Override": "YES" if row['policy_override_applied'] else "NO"
    }
    
    st.markdown(render_detail_card(detail_data, "Transaction Snapshot"), unsafe_allow_html=True)
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    
    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("✅ Approve Transaction", type="primary", use_container_width=True):
            update_status(selected_id, "APPROVED")
    with bc2:
        if st.button("🚫 Block Transaction", use_container_width=True):
            update_status(selected_id, "BLOCKED")
            
    st.markdown('<hr style="border-color:var(--border);margin:32px 0;">', unsafe_allow_html=True)
    
    st.markdown(section_header("Explainable AI (Feature Contributions)"), unsafe_allow_html=True)
    
    # Process features for XAI
    tx = row["transaction_json"] if isinstance(row.get("transaction_json"), str) else row.get("transaction_json", "{}")
    if isinstance(tx, str):
        try: tx = json.loads(tx)
        except: tx = {}
        
    try:
        from src.features import build_features, load_feature_config
        from src.xai import explain_prediction
        import plotly.graph_objects as go
        
        config = load_feature_config()
        features_df = build_features(tx, config)
        xai_res = explain_prediction(PROJECT_ROOT, features_df)
        
        if "error" in xai_res:
            st.warning("XAI Model not loaded or unavailable.")
        else:
            conf_val = xai_res["confidence"] * 100
            theme = st.session_state.get("theme", "light")
            conf_color = "var(--status-low)" if conf_val > 70 else "var(--status-high)" if conf_val > 40 else "var(--status-critical)"
            
            st.markdown(f"""
            <div style="margin-bottom:15px;display:flex;align-items:center;gap:10px;">
                <span style="font-size:12px;color:var(--text-secondary);text-transform:uppercase;">Model Confidence</span>
                <span style="font-size:16px;font-weight:600;color:{conf_color};">{conf_val:.1f}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            contributors = xai_res["contributors"]
            
            if contributors:
                fig = go.Figure()
                contributors.sort(key=lambda x: x["contribution"])
                y_labels = [c["feature"] for c in contributors]
                x_vals = [c["contribution"] for c in contributors]
                
                if theme == "dark":
                    colors = ["#E24B4A" if c > 0 else "#185FA5" for c in x_vals]
                else:
                    colors = ["#E24B4A" if c > 0 else "#185FA5" for c in x_vals]
                
                fig.add_trace(go.Bar(
                    x=x_vals, y=y_labels, orientation='h',
                    marker_color=colors,
                    text=[f"{c:.3f}" for c in x_vals],
                    textposition='outside',
                ))
                
                fig.update_layout(
                    height=max(250, len(contributors) * 30),
                    margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="gray", family="Inter"),
                    xaxis=dict(title="Contribution to Fraud Probability", gridcolor="rgba(100,100,100,0.1)", zerolinecolor="rgba(100,100,100,0.2)"),
                    yaxis=dict(gridcolor="rgba(100,100,100,0.1)"),
                    showlegend=False
                )
                
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No significant features to display.")
    except Exception as e:
        st.error(f"Error generating XAI explanation: {e}")
    
    if row.get("policy_override_applied"):
        st.markdown(section_header("Policy Reasons Triggered"), unsafe_allow_html=True)
        reasons_raw = row.get("policy_reasons_json", "[]")
        if isinstance(reasons_raw, str):
            try: reasons = json.loads(reasons_raw)
            except: reasons = []
        else:
            reasons = reasons_raw
            
        for r in reasons:
            st.error(f"🚨 {r}")

# ── LLM COPILOT SECTION ─────────────────────────────────────────────────────
st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
st.markdown(section_header("🤖 AI Copilot — Analyst Assistant"), unsafe_allow_html=True)

st.markdown("""
<div class="glass-card" style="padding:16px 20px;margin-bottom:20px;">
  <p style="color:var(--text-secondary);font-size:13px;margin:0;">
    Ask the AI Copilot to explain <em>why</em> this transaction was flagged in plain English,
    or ask follow-up questions like <strong>"Has this account type been flagged before?"</strong>
    <br><span style="font-size:11px;color:var(--accent);">
      ⚠️ Copilot is a decision-support tool. All LLM explanations are logged for audit compliance.
    </span>
  </p>
</div>
""", unsafe_allow_html=True)

# ── Per-case chat state ───────────────────────────────────────────────────────
chat_key = f"copilot_chat_{selected_id}"
if chat_key not in st.session_state:
    st.session_state[chat_key] = []  # List of {"role": "user"|"assistant", "content": str}

chat_history = st.session_state[chat_key]

# ── Render existing chat history ──────────────────────────────────────────────
for msg in chat_history:
    role_label = "🧑 Analyst" if msg["role"] == "user" else "🤖 Copilot"
    bubble_style = (
        "background:var(--accent-soft);border-left:3px solid var(--accent);"
        if msg["role"] == "user"
        else "background:var(--bg-surface);border-left:3px solid var(--status-medium);"
    )
    st.markdown(
        f"""<div style="padding:12px 16px;border-radius:8px;margin-bottom:10px;{bubble_style}">
            <span style="font-size:11px;font-weight:600;color:var(--text-secondary);
                         text-transform:uppercase;letter-spacing:0.05em;">{role_label}</span>
            <p style="margin:6px 0 0;color:var(--text-primary);font-size:14px;
                      line-height:1.6;white-space:pre-wrap;">{msg["content"]}</p>
        </div>""",
        unsafe_allow_html=True,
    )

# ── Action buttons + input ────────────────────────────────────────────────────
btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1.5])

with btn_col1:
    ask_clicked = st.button(
        "🤖 Ask Copilot" if not chat_history else "🔄 Re-Explain",
        use_container_width=True,
        type="primary",
    )

with btn_col2:
    if chat_history and st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state[chat_key] = []
        st.rerun()

follow_up_text = st.text_input(
    "Ask a follow-up question (optional):",
    placeholder="e.g. Has this account type been flagged before? What does balance_error mean?",
    key=f"copilot_followup_{selected_id}",
)

# ── Execute copilot request ───────────────────────────────────────────────────
def _call_copilot(log_id: int, follow_up: str = None) -> str:
    """Call the FastAPI /copilot/explain endpoint and return the explanation text."""
    payload = {"prediction_log_id": int(log_id)}
    if follow_up:
        payload["follow_up"] = follow_up
    try:
        resp = requests.post(
            "http://localhost:8000/copilot/explain",
            json=payload,
            timeout=20,  # Extra buffer over the 15s API timeout
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("error") and not data.get("explanation"):
                return f"⚠️ Copilot unavailable: {data['error']}\n\nPlease refer to the SHAP waterfall chart above for analysis."
            return data.get("explanation") or "⚠️ No explanation returned."
        return f"⚠️ API error (HTTP {resp.status_code}). Please use the SHAP chart above."
    except requests.exceptions.Timeout:
        return "⚠️ The Copilot request timed out. This can happen during high API load. Please use the SHAP chart above for analysis."
    except Exception as e:
        return f"⚠️ Copilot unavailable ({type(e).__name__}). Please refer to the SHAP chart above."


if ask_clicked or (follow_up_text and st.session_state.get(f"_prev_followup_{selected_id}") != follow_up_text):
    # Track follow-up to detect when user submits a new one
    st.session_state[f"_prev_followup_{selected_id}"] = follow_up_text

    # Determine question: initial or follow-up
    if follow_up_text and chat_history:
        question = follow_up_text
        # Add analyst question to history
        st.session_state[chat_key].append({"role": "user", "content": question})
    else:
        question = None  # Initial explanation request

    with st.spinner("🤖 Copilot is analysing the transaction..."):
        response_text = _call_copilot(selected_id, follow_up=question)

    # Append copilot response to history
    st.session_state[chat_key].append({"role": "assistant", "content": response_text})
    st.rerun()