import streamlit as st
import sys
from pathlib import Path
import asyncio
import time
import pandas as pd
import plotly.graph_objects as go
from collections import deque

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from src.stream_simulator import generate_transaction_stream

st.set_page_config(page_title="Live Stream", page_icon="📡", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_dashboard")

with st.sidebar:
    display_user_profile()

st.markdown('<div class="page-title">Live Transaction <span class="gradient-word">Stream</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Real-time inference and velocity monitoring</div>', unsafe_allow_html=True)

# ── Stream Controls ───────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    stream_active = st.toggle("🟢 Start Live Stream", value=False)
with c2:
    burst_mode = st.toggle("💥 Enable Fraud Bursts", value=False)
with c3:
    st.markdown('<div style="font-size:12px;color:#8899AA;padding-top:10px;">Simulates WebSocket connection to payment gateway</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Layout Elements ───────────────────────────────────────────────────────────
metric_cols = st.columns(4)
m_vol = metric_cols[0].empty()
m_fps = metric_cols[1].empty()
m_amt = metric_cols[2].empty()
m_frd = metric_cols[3].empty()

chart_spot = st.empty()
table_spot = st.empty()

# ── State Initialization ──────────────────────────────────────────────────────
if "stream_data" not in st.session_state:
    st.session_state.stream_data = deque(maxlen=50) # Keep last 50
if "stream_stats" not in st.session_state:
    st.session_state.stream_stats = {"count": 0, "fraud_count": 0, "total_amount": 0.0, "start_time": time.time()}

# ── Async Stream Loop ─────────────────────────────────────────────────────────
async def process_stream():
    async for tx in generate_transaction_stream(burst_fraud=burst_mode, delay_ms=800):
        if not stream_active:
            break
            
        # Update State
        st.session_state.stream_data.appendleft(tx)
        st.session_state.stream_stats["count"] += 1
        st.session_state.stream_stats["total_amount"] += tx.get("amount", 0)
        if tx.get("is_fraud_injected"):
            st.session_state.stream_stats["fraud_count"] += 1
            
        # Compute Metrics
        stats = st.session_state.stream_stats
        elapsed = time.time() - stats["start_time"]
        tps = stats["count"] / elapsed if elapsed > 0 else 0
        fraud_rate = (stats["fraud_count"] / stats["count"] * 100) if stats["count"] > 0 else 0
        
        # Render Metrics
        m_vol.markdown(f"""
        <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);border-radius:8px;padding:15px;">
            <div style="font-size:11px;color:#8899AA;text-transform:uppercase;">Processed</div>
            <div style="font-size:24px;font-weight:700;color:#E8F0FF;">{stats['count']:,}</div>
        </div>
        """, unsafe_allow_html=True)
        
        m_fps.markdown(f"""
        <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);border-radius:8px;padding:15px;">
            <div style="font-size:11px;color:#8899AA;text-transform:uppercase;">Velocity (TPS)</div>
            <div style="font-size:24px;font-weight:700;color:#00B4FF;">{tps:.1f}/s</div>
        </div>
        """, unsafe_allow_html=True)
        
        m_amt.markdown(f"""
        <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);border-radius:8px;padding:15px;">
            <div style="font-size:11px;color:#8899AA;text-transform:uppercase;">Volume Seen</div>
            <div style="font-size:24px;font-weight:700;color:#00E676;">₹{stats['total_amount']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        fr_color = "#FF2D55" if fraud_rate > 5 else "#FF8A00" if fraud_rate > 2 else "#E8F0FF"
        m_frd.markdown(f"""
        <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);border-radius:8px;padding:15px;">
            <div style="font-size:11px;color:#8899AA;text-transform:uppercase;">Fraud Attack Rate</div>
            <div style="font-size:24px;font-weight:700;color:{fr_color};">{fraud_rate:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Render Table
        df = pd.DataFrame(list(st.session_state.stream_data))
        if not df.empty:
            df["Time"] = pd.to_datetime(df["timestamp"]).dt.strftime("%H:%M:%S.%f").str[:-3]
            df["Risk"] = df["is_fraud_injected"].apply(lambda x: "🚨 CRITICAL" if x else "✅ LOW")
            df["Amount"] = df["amount"].apply(lambda x: f"₹{x:,.2f}")
            display_df = df[["Time", "nameOrig", "type", "Amount", "Risk"]].head(15)
            
            with table_spot.container():
                st.markdown('<div class="section-label">Real-Time Ledger</div>', unsafe_allow_html=True)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
            # Render velocity chart
            with chart_spot.container():
                st.markdown('<div class="section-label">Attack Velocity</div>', unsafe_allow_html=True)
                df['is_fraud_int'] = df['is_fraud_injected'].astype(int)
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=df['amount'][::-1], mode='lines', name='Amount', line=dict(color='#00B4FF', width=1)))
                
                # Highlight frauds
                frauds = df[df['is_fraud_injected'] == True]
                if not frauds.empty:
                    fig.add_trace(go.Scatter(x=frauds.index[::-1], y=frauds['amount'][::-1], mode='markers', name='Fraud Alert',
                                             marker=dict(color='#FF2D55', size=10, symbol='circle-open', line=dict(width=2))))
                                             
                fig.update_layout(
                    height=200, margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#8899AA"), showlegend=False,
                    xaxis=dict(showgrid=False, showticklabels=False),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                
        # Must await sleep to let Streamlit yield control
        await asyncio.sleep(0.1)

if stream_active:
    asyncio.run(process_stream())
else:
    st.info("Toggle 'Start Live Stream' to begin monitoring real-time transactions.")
    
    # Reset stats if stopped
    if st.session_state.stream_stats["count"] > 0:
        if st.button("Reset Stream Data"):
            st.session_state.stream_data.clear()
            st.session_state.stream_stats = {"count": 0, "fraud_count": 0, "total_amount": 0.0, "start_time": time.time()}
            st.rerun()
