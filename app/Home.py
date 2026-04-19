from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from app.utils_dashboard import get_db_path, load_logs_df, get_total_count
from app.premium_theme import inject_premium_theme

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Fraud Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

inject_premium_theme()

# ========== LOAD DATA ==========
DB_PATH = get_db_path(PROJECT_ROOT)
total_count = get_total_count(DB_PATH)
df = load_logs_df(DB_PATH, limit=10000)

# ========== HEADER (Enhanced) ==========
col_h1, col_h2 = st.columns([3, 1])

with col_h1:
    st.markdown("# Transaction Fraud Intelligence")
    st.markdown('<p class="subtitle">Real-time Risk Monitoring & Policy Engine</p>', 
                unsafe_allow_html=True)

with col_h2:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

st.markdown("---")

# ========== CHECK DATA ==========
if df.empty:
    st.info("⚠️ No transaction logs found. Generate sample data via API: `/admin/seed-logs?count=2000`")
    st.stop()

# ========== CALCULATE METRICS ==========
critical = int((df["final_risk_level"] == "CRITICAL").sum())
high = int((df["final_risk_level"] == "HIGH").sum())
override_rate = float(df["policy_override_applied"].mean() * 100)
avg_score = float(df["final_risk_score"].mean())

# ========== KPI CARDS ==========
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric(
        label="Total Transactions",
        value=f"{total_count:,}",
        delta="All time"
    )

with c2:
    st.metric(
        label="Critical Alerts",
        value=f"{critical:,}",
        delta=f"{critical/total_count*100:.2f}%" if total_count else "0%"
    )

with c3:
    st.metric(
        label="High Risk",
        value=f"{high:,}",
        delta=f"{high/total_count*100:.2f}%" if total_count else "0%"
    )

with c4:
    st.metric(
        label="Policy Overrides",
        value=f"{override_rate:.1f}%",
        delta=f"{int(df['policy_override_applied'].sum()):,} cases"
    )

with c5:
    st.metric(
        label="Avg Risk Score",
        value=f"{avg_score:.0f}",
        delta="out of 100"
    )

st.markdown("---")

# ========== CHARTS ROW ==========
chart_left, chart_right = st.columns([1, 1])

# ---- RISK DISTRIBUTION (Premium Donut) ----
with chart_left:
    st.markdown("### Risk Distribution")
    
    dist_data = df["final_risk_level"].value_counts()
    
    fig_donut = go.Figure(data=[go.Pie(
        labels=dist_data.index,
        values=dist_data.values,
        hole=0.65,
        marker=dict(
            colors=['#86EFAC', '#FCD34D', '#FDBA74', '#FCA5A5'],
            line=dict(color='#0B1220', width=3)
        ),
        textfont=dict(size=13, color='white', family='Inter', weight=600),
        hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>%{percent}<extra></extra>'
    )])
    
    fig_donut.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color='#CBD5E1', family='Inter')
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=80),
        height=380,
        annotations=[dict(
            text=f'<b>{total_count:,}</b><br><span style="font-size:11px;color:#94A3B8;font-weight:500">TOTAL</span>',
            x=0.5, y=0.5,
            font=dict(size=32, color='#F8FAFC', family='Inter'),
            showarrow=False
        )]
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)

# ---- ALERTS TREND (Enhanced Smooth Line) ----
with chart_right:
    st.markdown("### Alert Trend (Last 14 Days)")
    
    tmp = df.dropna(subset=["created_at"]).copy()
    tmp = tmp[tmp["final_risk_level"].isin(["HIGH", "CRITICAL"])]
    
    if tmp.empty:
        st.info("No high-risk alerts in current dataset")
    else:
        tmp["date"] = tmp["created_at"].dt.floor("D")
        alerts_by_date = tmp.groupby("date").size().reset_index(name="count")
        alerts_by_date = alerts_by_date.tail(14)
        
        fig_line = go.Figure()
        
        # ✅ ENHANCED: Smooth spline + gradient fill
        fig_line.add_trace(go.Scatter(
            x=alerts_by_date["date"],
            y=alerts_by_date["count"],
            mode='lines',
            fill='tozeroy',
            line=dict(
                color='#EF4444',
                width=3,
                shape='spline',  # ✅ Smooth curve
                smoothing=1.2
            ),
            fillcolor='rgba(239, 68, 68, 0.2)',  # ✅ Gradient fill
            fillgradient=dict(
                type='vertical',
                colorscale=[[0, 'rgba(239, 68, 68, 0)'], [1, 'rgba(239, 68, 68, 0.25)']]
            ),
            hovertemplate='<b>%{x|%b %d}</b><br>Alerts: %{y:,}<extra></extra>'
        ))
        
        fig_line.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30, 41, 59, 0.25)',
            margin=dict(l=20, r=20, t=40, b=40),
            height=380,
            xaxis=dict(
                showgrid=False,  # ✅ Clean x-axis
                color='#94A3B8',
                tickfont=dict(size=11, family='Inter', weight=500)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(148, 163, 184, 0.06)',  # ✅ Subtle grid
                color='#94A3B8',
                tickfont=dict(size=11, family='Inter', weight=500)
            ),
            font=dict(family='Inter', color='#CBD5E1'),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='rgba(30, 41, 59, 0.95)',
                font=dict(family='Inter', size=12, color='white'),
                bordercolor='rgba(148, 163, 184, 0.2)'
            )
        )
        
        st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

# ========== OVERRIDE INSIGHTS ==========
st.markdown("### Policy Override Analysis")

override_df = df[df["policy_override_applied"] == 1]

if not override_df.empty:
    ins_c1, ins_c2 = st.columns([1, 2])
    
    with ins_c1:
        st.metric(
            "Override Count",
            f"{len(override_df):,}",
            delta=f"{len(override_df)/len(df)*100:.1f}% of total"
        )
    
    with ins_c2:
        all_reasons = []
        for reasons in override_df["policy_reasons"]:
            all_reasons.extend(reasons)
        
        if all_reasons:
            top_reasons = pd.Series(all_reasons).value_counts().head(4)
            
            st.markdown("**Top Triggers:**")
            for reason, count in top_reasons.items():
                pct = count / len(override_df) * 100
                st.markdown(f"""
                <div style="display:flex;align-items:center;margin:0.75rem 0;gap:0.75rem;">
                    <span class="badge badge-high">{count}</span>
                    <span style="color:#E2E8F0;font-size:0.875rem;font-weight:500;">{reason}</span>
                    <span style="color:#64748B;font-size:0.75rem;font-weight:500;">({pct:.1f}%)</span>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("No policy overrides detected in current logs")

st.markdown("---")

# ========== TRANSACTIONS TABLE ==========
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
    height=500,
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
    '<p class="caption" style="text-align:center;font-weight:500;">Transaction Fraud Intelligence System • Built with ML + Python</p>',
    unsafe_allow_html=True
)