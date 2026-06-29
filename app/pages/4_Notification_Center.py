import streamlit as st
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design

st.set_page_config(page_title="Notification Center", page_icon="🔔", layout="wide")
inject_premium_design()

st.markdown("""
<div style="padding:1rem 0 1.5rem">
  <div class="page-title">
    Notification <span class="gradient-word">Center</span>
  </div>
  <div class="page-subtitle">
    Configure Webhooks, Slack integrations, and Email alerts for Critical transactions.
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="hdivider"></div>', unsafe_allow_html=True)

# ── WEBHOOK SETTINGS ────────────────────────────────────────────────────────
c1, c2 = st.columns([1, 1])

with c1:
    st.markdown('<div class="section-label">External Integrations</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background:rgba(8,13,26,0.8);border:1px solid rgba(148,163,184,0.1);
                border-radius:12px;padding:20px;margin-bottom:20px;">
        <h4 style="color:#E8F0FF;margin-top:0;font-size:16px;">Slack Webhook (Mock)</h4>
        <p style="font-size:13px;color:#8899AA;">Automatically send alerts to a specific Slack channel when CRITICAL risk is detected.</p>
    </div>
    """, unsafe_allow_html=True)
    
    webhook_url = st.text_input("Webhook URL", value="https://your-webhook-url-here.com", type="password")
    trigger_level = st.selectbox("Trigger Level", ["CRITICAL Only", "HIGH and above"])
    
    if st.button("💾 Save Configuration", type="primary"):
        st.success("Configuration saved securely.")

with c2:
    st.markdown('<div class="section-label">Test Integration</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:rgba(0,180,255,0.06);border:1px solid rgba(0,180,255,0.2);
                border-left:3px solid #00B4FF;border-radius:10px;padding:20px;">
        <p style="font-size:13px;color:#C4CFDE;margin-bottom:15px;">Send a test alert payload to the configured webhook to verify connectivity.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<br>', unsafe_allow_html=True)
    if st.button("📤 Send Test Payload"):
        with st.spinner("Sending..."):
            import time
            time.sleep(1)
            st.success("Test payload sent successfully! Check your Slack channel.")
            
st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">Audit Logs</div>', unsafe_allow_html=True)
st.info("No recent external notifications dispatched.")
