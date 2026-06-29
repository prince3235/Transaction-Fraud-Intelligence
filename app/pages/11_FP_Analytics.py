import streamlit as st
import sys
from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.premium_design import inject_premium_design
from app.auth_guard import require_auth, display_user_profile
from app.utils_dashboard import get_db_path

st.set_page_config(page_title="False Positive Analytics", page_icon="🎯", layout="wide")
inject_premium_design()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
require_auth(permission="view_model")
DB_PATH = get_db_path(PROJECT_ROOT)

with st.sidebar:
    display_user_profile()

st.markdown('<div class="page-title">False Positive <span class="gradient-word">Analytics</span></div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Measure alert accuracy and optimize analyst review time</div>', unsafe_allow_html=True)


# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_fp_data():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    
    # Cases to measure accuracy
    cases = pd.read_sql_query("SELECT case_id, status, assigned_to, created_at, resolved_at FROM fraud_cases", con)
    
    fp_rate = 0.0
    avg_review_time = 0.0
    analyst_stats = pd.DataFrame()
    
    if not cases.empty:
        total_resolved = len(cases[cases['status'].isin(['Resolved', 'False_Positive'])])
        total_fp = len(cases[cases['status'] == 'False_Positive'])
        
        if total_resolved > 0:
            fp_rate = (total_fp / total_resolved) * 100
            
        # Review time calculation
        resolved_cases = cases[cases['resolved_at'].notna()].copy()
        if not resolved_cases.empty:
            resolved_cases['created'] = pd.to_datetime(resolved_cases['created_at'])
            resolved_cases['resolved'] = pd.to_datetime(resolved_cases['resolved_at'])
            resolved_cases['review_mins'] = (resolved_cases['resolved'] - resolved_cases['created']).dt.total_seconds() / 60.0
            avg_review_time = resolved_cases['review_mins'].mean()
            
            # Analyst stats
            analyst_stats = resolved_cases.groupby('assigned_to').agg(
                cases_reviewed=('case_id', 'count'),
                fps=('status', lambda x: (x == 'False_Positive').sum()),
                avg_time_mins=('review_mins', 'mean')
            ).reset_index()
            
            analyst_stats['fp_rate'] = (analyst_stats['fps'] / analyst_stats['cases_reviewed']) * 100
            
    con.close()
    return {
        "fp_rate": fp_rate,
        "avg_review_time": avg_review_time,
        "analyst_stats": analyst_stats,
        "cases": cases
    }

data = fetch_fp_data()


# ── KPI Row ───────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)

fp_color = "#00E676" if data['fp_rate'] < 10 else "#FF8A00" if data['fp_rate'] < 30 else "#FF2D55"

c1.markdown(f"""
<div class="kpi-card kpi-orange">
  <div class="kpi-stripe"></div><div class="kpi-glow-blob"></div>
  <div class="kpi-label">Overall False Positive Rate</div>
  <div style="font-size:32px;font-weight:800;color:{fp_color};">{data['fp_rate']:.1f}%</div>
  <div class="kpi-sub">Alerts that were actually legitimate</div>
</div>
""", unsafe_allow_html=True)

c2.markdown(f"""
<div class="kpi-card kpi-blue">
  <div class="kpi-stripe"></div><div class="kpi-glow-blob"></div>
  <div class="kpi-label">Average Investigation Time</div>
  <div class="kpi-value">{data['avg_review_time']:.1f} mins</div>
  <div class="kpi-sub">Time spent per case</div>
</div>
""", unsafe_allow_html=True)

# Projected wasted time
wasted_hours = (data['fp_rate'] / 100.0) * len(data['cases']) * data['avg_review_time'] / 60.0

c3.markdown(f"""
<div class="kpi-card kpi-purple">
  <div class="kpi-stripe"></div><div class="kpi-glow-blob"></div>
  <div class="kpi-label">Operational Waste (Projected)</div>
  <div class="kpi-value">{wasted_hours:.1f} hrs</div>
  <div class="kpi-sub">Time spent reviewing False Positives</div>
</div>
""", unsafe_allow_html=True)


# ── Analyst Leaderboard ───────────────────────────────────────────────────────
st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">Analyst Accuracy Leaderboard</div>', unsafe_allow_html=True)

df_analyst = data['analyst_stats']
if not df_analyst.empty:
    # Sort by lowest FP rate
    df_analyst = df_analyst.sort_values('fp_rate', ascending=True)
    
    st.dataframe(
        df_analyst,
        use_container_width=True,
        hide_index=True,
        column_config={
            "assigned_to": "Analyst",
            "cases_reviewed": "Cases Reviewed",
            "fps": "False Positives Flagged",
            "fp_rate": st.column_config.NumberColumn("FP Rate (%)", format="%.1f%%"),
            "avg_time_mins": st.column_config.NumberColumn("Avg Review Time (mins)", format="%.1f")
        }
    )
else:
    st.info("Not enough resolved cases to build leaderboard.")
    
# ── Charts ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">Case Resolution Breakdown</div>', unsafe_allow_html=True)

cases_df = data['cases']
if not cases_df.empty:
    status_counts = cases_df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    
    fig = px.pie(status_counts, values='count', names='status', hole=0.7,
                 color='status',
                 color_discrete_map={
                     "Open": "#00B4FF", "Investigating": "#FFB800",
                     "Escalated": "#FF2D55", "Resolved": "#00E676",
                     "False_Positive": "#A855F7"
                 })
    fig.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8899AA")
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
