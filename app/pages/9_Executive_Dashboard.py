import streamlit as st
import sys
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path
from src.auth import log_audit_event

st.set_page_config(page_title="Executive Analytics", page_icon="📈", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_executive")
user = st.session_state.user
DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

st.markdown('<div class="page-title">Executive <span class="gradient-word">Analytics</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">High-level financial impact and risk KPIs</div>', unsafe_allow_html=True)


# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_kpis():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    
    # Financial Impact
    df = pd.read_sql_query("SELECT final_risk_level, status, transaction_json, created_at FROM prediction_logs", con)
    
    if df.empty:
        return None
        
    df['amount'] = df['transaction_json'].apply(lambda x: float(eval(x).get('amount', 0)) if isinstance(x, str) else 0)
    df['date'] = pd.to_datetime(df['created_at']).dt.date
    
    total_vol = df['amount'].sum()
    
    # Blocked = Saved Revenue
    saved = df[df['status'] == 'BLOCKED']['amount'].sum()
    
    # False Negative (simulated) = HIGH/CRITICAL that were APPROVED
    potential_loss = df[(df['status'] == 'APPROVED') & (df['final_risk_level'].isin(['HIGH', 'CRITICAL']))]['amount'].sum()
    
    # Alert SLA (Avg time from PENDING to RESOLVED in fraud_cases)
    cases = pd.read_sql_query("SELECT created_at, resolved_at FROM fraud_cases WHERE resolved_at IS NOT NULL", con)
    sla_hours = 0
    if not cases.empty:
        cases['created'] = pd.to_datetime(cases['created_at'])
        cases['resolved'] = pd.to_datetime(cases['resolved_at'])
        sla_hours = (cases['resolved'] - cases['created']).dt.total_seconds().mean() / 3600.0
    
    con.close()
    return {
        "total_vol": total_vol,
        "saved": saved,
        "potential_loss": potential_loss,
        "sla_hours": sla_hours,
        "df": df
    }

kpi_data = fetch_kpis()
if not kpi_data:
    st.info("No data available.")
    st.stop()


# ── KPI Row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

saved_pct = (kpi_data["saved"] / kpi_data["total_vol"] * 100) if kpi_data["total_vol"] else 0

c1.markdown(f"""
<div style="background:rgba(8,13,26,0.8);border:1px solid rgba(0,230,118,0.2);border-left:4px solid #00E676;border-radius:12px;padding:20px;">
    <div style="font-size:12px;color:#8899AA;text-transform:uppercase;">Revenue Saved (Blocked)</div>
    <div style="font-size:28px;font-weight:800;color:#00E676;">₹{kpi_data['saved']:,.0f}</div>
    <div style="font-size:11px;color:#BAC4D0;">{saved_pct:.2f}% of total volume</div>
</div>
""", unsafe_allow_html=True)

c2.markdown(f"""
<div style="background:rgba(8,13,26,0.8);border:1px solid rgba(255,45,85,0.2);border-left:4px solid #FF2D55;border-radius:12px;padding:20px;">
    <div style="font-size:12px;color:#8899AA;text-transform:uppercase;">Potential Loss Avoided</div>
    <div style="font-size:28px;font-weight:800;color:#FF2D55;">₹{kpi_data['potential_loss']:,.0f}</div>
    <div style="font-size:11px;color:#BAC4D0;">High risk allowed transactions</div>
</div>
""", unsafe_allow_html=True)

df = kpi_data['df']
high_risk_pct = (len(df[df['final_risk_level'].isin(['HIGH', 'CRITICAL'])]) / len(df) * 100) if len(df) else 0

c3.markdown(f"""
<div style="background:rgba(8,13,26,0.8);border:1px solid rgba(255,138,0,0.2);border-left:4px solid #FF8A00;border-radius:12px;padding:20px;">
    <div style="font-size:12px;color:#8899AA;text-transform:uppercase;">Overall Fraud Rate</div>
    <div style="font-size:28px;font-weight:800;color:#FF8A00;">{high_risk_pct:.1f}%</div>
    <div style="font-size:11px;color:#BAC4D0;">Of {len(df):,} total transactions</div>
</div>
""", unsafe_allow_html=True)

sla_color = "#00E676" if kpi_data['sla_hours'] < 2 else "#FF8A00"

c4.markdown(f"""
<div style="background:rgba(8,13,26,0.8);border:1px solid rgba(0,180,255,0.2);border-left:4px solid #00B4FF;border-radius:12px;padding:20px;">
    <div style="font-size:12px;color:#8899AA;text-transform:uppercase;">Avg Resolution SLA</div>
    <div style="font-size:28px;font-weight:800;color:{sla_color};">{kpi_data['sla_hours']:.1f} hrs</div>
    <div style="font-size:11px;color:#BAC4D0;">From open to resolved</div>
</div>
""", unsafe_allow_html=True)


# ── Charts ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

col_ch1, col_ch2 = st.columns(2)

with col_ch1:
    st.markdown('<div class="section-label">Financial Impact Trend</div>', unsafe_allow_html=True)
    daily_stats = df.groupby(['date', 'status'])['amount'].sum().unstack(fill_value=0).reset_index()
    
    fig = go.Figure()
    if 'APPROVED' in daily_stats:
        fig.add_trace(go.Scatter(x=daily_stats['date'], y=daily_stats['APPROVED'], mode='lines', name='Processed Volume', line=dict(color='#00B4FF', width=2)))
    if 'BLOCKED' in daily_stats:
        fig.add_trace(go.Scatter(x=daily_stats['date'], y=daily_stats['BLOCKED'], mode='lines', fill='tozeroy', name='Saved (Blocked)', line=dict(color='#00E676', width=2)))
        
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8899AA"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col_ch2:
    st.markdown('<div class="section-label">Action Distribution by Risk</div>', unsafe_allow_html=True)
    risk_action = df.groupby(['final_risk_level', 'status']).size().reset_index(name='count')
    
    fig = px.bar(risk_action, x='final_risk_level', y='count', color='status',
                 color_discrete_map={"APPROVED": "#00E676", "PENDING_REVIEW": "#FF8A00", "BLOCKED": "#FF2D55"},
                 category_orders={"final_risk_level": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]})
                 
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8899AA"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
