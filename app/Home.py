from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from app.utils_dashboard import get_db_path, load_logs_df, get_total_count
from app.premium_design import inject_premium_design

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Fraud Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

inject_premium_design()

# ========== LOAD DATA ==========
DB_PATH = get_db_path(PROJECT_ROOT)
total_count = get_total_count(DB_PATH)
df = load_logs_df(DB_PATH, limit=10000)

# ========== HEADER ==========
col_h1, col_h2 = st.columns([3.5, 1])

with col_h1:
    st.markdown("# Fraud Intelligence Platform")
    st.markdown('<p class="subtitle">Real-time Transaction Monitoring & Risk Intelligence System</p>', 
                unsafe_allow_html=True)

with col_h2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

st.markdown("---")

# ========== DATA CHECK ==========
if df.empty:
    st.info("⚠️ No transaction logs found. Generate sample data: `/admin/seed-logs?count=2000`")
    st.stop()

# ========== METRICS ==========
critical = int((df["final_risk_level"] == "CRITICAL").sum())
high = int((df["final_risk_level"] == "HIGH").sum())
override_rate = float(df["policy_override_applied"].mean() * 100)
avg_score = float(df["final_risk_score"].mean())

# ========== KPI CARDS ==========
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric(
        label="Total Transactions",
        value=f"{total_count:,}",
        delta="All time"
    )

with m2:
    st.metric(
        label="Critical Alerts",
        value=f"{critical:,}",
        delta=f"{critical/total_count*100:.2f}%" if total_count else "0%"
    )

with m3:
    st.metric(
        label="High Risk",
        value=f"{high:,}",
        delta=f"{high/total_count*100:.2f}%" if total_count else "0%"
    )

with m4:
    st.metric(
        label="Override Rate",
        value=f"{override_rate:.1f}%",
        delta=f"{int(df['policy_override_applied'].sum()):,} triggers"
    )

with m5:
    st.metric(
        label="Avg Risk Score",
        value=f"{avg_score:.0f}",
        delta="/ 100"
    )

st.markdown("---")

# ========== CHARTS ==========
chart_left, chart_right = st.columns([1, 1])

# ---- DONUT CHART (Enhanced) ----
with chart_left:
    st.markdown("### Risk Distribution")
    
    dist_data = df["final_risk_level"].value_counts()
    
    fig_donut = go.Figure(data=[go.Pie(
        labels=dist_data.index,
        values=dist_data.values,
        hole=0.7,
        marker=dict(
            colors=['#86EFAC', '#FCD34D', '#FDBA74', '#F87171'],
            line=dict(color='#0A0E1A', width=3)
        ),
        textfont=dict(size=14, color='#F1F5F9', family='Inter', weight=700),
        textposition='outside',
        hovertemplate='<b>%{label}</b><br>%{value:,} transactions<br>%{percent}<extra></extra>'
    )])
    
    fig_donut.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=13, color='#CBD5E1', family='Inter', weight=600)
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=30, b=100),
        height=420,
        annotations=[dict(
            text=f'<b style="font-size:38px;color:#F8FAFC">{total_count:,}</b><br>'
                 f'<span style="font-size:12px;color:#94A3B8;font-weight:700;letter-spacing:0.1em">TOTAL</span>',
            x=0.5, y=0.5,
            font=dict(family='Inter'),
            showarrow=False
        )]
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)

# ---- LINE CHART (Premium Blue) ----
with chart_right:
    st.markdown("### Alert Trend (14 Days)")
    
    tmp = df.dropna(subset=["created_at"]).copy()
    tmp = tmp[tmp["final_risk_level"].isin(["HIGH", "CRITICAL"])]
    
    if tmp.empty:
        st.info("No high-risk alerts")
    else:
        tmp["date"] = tmp["created_at"].dt.floor("D")
        alerts = tmp.groupby("date").size().reset_index(name="count")
        alerts = alerts.tail(14)
        
        fig_line = go.Figure()
        
        fig_line.add_trace(go.Scatter(
            x=alerts["date"],
            y=alerts["count"],
            mode='lines+markers',
            fill='tozeroy',
            line=dict(
                color='#3B82F6',
                width=3.5,
                shape='spline',
                smoothing=1.3
            ),
            marker=dict(
                color='#3B82F6',
                size=9,
                line=dict(color='#1D4ED8', width=2.5)
            ),
            fillcolor='rgba(59, 130, 246, 0)',
            fillgradient=dict(
                type='vertical',
                colorscale=[
                    [0, 'rgba(59, 130, 246, 0)'],
                    [0.5, 'rgba(59, 130, 246, 0.15)'],
                    [1, 'rgba(59, 130, 246, 0.3)']
                ]
            ),
            hovertemplate='<b>%{x|%b %d, %Y}</b><br>Alerts: <b>%{y:,}</b><extra></extra>'
        ))
        
        fig_line.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(17, 24, 39, 0.4)',
            margin=dict(l=10, r=10, t=30, b=40),
            height=420,
            xaxis=dict(
                showgrid=False,
                color='#94A3B8',
                tickfont=dict(size=12, family='Inter', weight=600)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.06)',
                color='#94A3B8',
                tickfont=dict(size=12, family='Inter', weight=600),
                zeroline=False
            ),
            font=dict(family='Inter', color='#CBD5E1'),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='rgba(17, 24, 39, 0.98)',
                font=dict(family='Inter', size=13, color='#F1F5F9'),
                bordercolor='rgba(59, 130, 246, 0.4)'
            )
        )
        
        st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

# ========== OVERRIDE INSIGHTS ==========
st.markdown("### Policy Override Analysis")

override_df = df[df["policy_override_applied"] == 1]

if not override_df.empty:
    oc1, oc2 = st.columns([1, 2.5])
    
    with oc1:
        st.metric(
            "Overrides",
            f"{len(override_df):,}",
            delta=f"{len(override_df)/len(df)*100:.1f}%"
        )
    
    with oc2:
        all_reasons = []
        for reasons in override_df["policy_reasons"]:
            all_reasons.extend(reasons)
        
        if all_reasons:
            top_reasons = pd.Series(all_reasons).value_counts().head(4)
            
            st.markdown("**Top Triggers:**")
            for reason, count in top_reasons.items():
                pct = count / len(override_df) * 100
                st.markdown(f"""
                <div style="display:flex;align-items:center;margin:0.875rem 0;gap:1rem;">
                    <span class="badge badge-high">{count}</span>
                    <span style="color:#E2E8F0;font-size:0.9375rem;font-weight:600;">{reason}</span>
                    <span style="color:#64748B;font-size:0.8125rem;font-weight:600;">({pct:.1f}%)</span>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("No overrides detected")

st.markdown("---")

# ========== TABLE ==========
st.markdown("### Recent Transactions")

table_df = df[[
    "id", "created_at", "ml_probability", "ml_risk_level",
    "final_risk_level", "final_risk_score", "policy_override_applied"
]].head(40).copy()

table_df["created_at"] = table_df["created_at"].dt.strftime("%Y-%m-%d %H:%M")
table_df["ml_probability"] = table_df["ml_probability"].round(4)

st.dataframe(
    table_df,
    use_container_width=True,
    height=520,
    column_config={
        "id": st.column_config.NumberColumn("ID", width="small"),
        "created_at": st.column_config.TextColumn("Timestamp", width="medium"),
        "ml_probability": st.column_config.NumberColumn("ML Prob", format="%.4f", width="small"),
        "ml_risk_level": st.column_config.TextColumn("ML Risk", width="small"),
        "final_risk_level": st.column_config.TextColumn("Final Risk", width="small"),
        "final_risk_score": st.column_config.NumberColumn("Score", width="small"),
        "policy_override_applied": st.column_config.CheckboxColumn("Override", width="small")
    },
    hide_index=True
)

# ========== FOOTER ==========
st.markdown("---")
st.markdown(
    '<p class="caption" style="text-align:center;font-weight:600;">Fraud Intelligence Platform • Built with ML + Python + Streamlit</p>',
    unsafe_allow_html=True
)