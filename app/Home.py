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
col_h1, col_h2 = st.columns([4, 1])

with col_h1:
    st.markdown("""
    <div class="page-header">
        <div class="header-badge">LIVE MONITORING</div>
        <h1>Fraud Intelligence<br><span class="gradient-text">Platform</span></h1>
        <p class="subtitle">Real-time Transaction Monitoring &amp; Risk Intelligence System</p>
    </div>
    """, unsafe_allow_html=True)

with col_h2:
    st.markdown('<div style="height:60px"></div>', unsafe_allow_html=True)
    if st.button("↻  Refresh Data", use_container_width=True):
        st.rerun()

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ========== DATA CHECK ==========
if df.empty:
    st.info("⚠️  No transaction logs found. Generate sample data via `/admin/seed-logs?count=2000`")
    st.stop()

# ========== METRICS ==========
critical  = int((df["final_risk_level"] == "CRITICAL").sum())
high      = int((df["final_risk_level"] == "HIGH").sum())
override_rate = float(df["policy_override_applied"].mean() * 100)
avg_score = float(df["final_risk_score"].mean())

# ========== KPI CARDS ==========
m1, m2, m3, m4, m5 = st.columns(5)

cards = [
    (m1, "Total Transactions", f"{total_count:,}",     "All time",                                                   "blue"),
    (m2, "Critical Alerts",    f"{critical:,}",         f"{critical/total_count*100:.2f}% of total" if total_count else "0%", "red"),
    (m3, "High Risk",          f"{high:,}",             f"{high/total_count*100:.2f}% of total"     if total_count else "0%", "orange"),
    (m4, "Override Rate",      f"{override_rate:.1f}%", f"{int(df['policy_override_applied'].sum()):,} triggers",    "purple"),
    (m5, "Avg Risk Score",     f"{avg_score:.0f}",      "out of 100",                                                 "teal"),
]

for col, label, value, delta, color in cards:
    with col:
        st.markdown(f"""
        <div class="kpi-card kpi-{color}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta">{delta}</div>
            <div class="kpi-glow"></div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ========== CHARTS ==========
chart_left, chart_right = st.columns([1, 1])

# ─── DONUT CHART ───────────────────────────────────────────────
with chart_left:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Risk Distribution</div>', unsafe_allow_html=True)

    dist_data = df["final_risk_level"].value_counts()

    DONUT_COLORS = {
        "LOW":      "#10B981",
        "MEDIUM":   "#F59E0B",
        "HIGH":     "#F97316",
        "CRITICAL": "#EF4444",
    }
    ordered_labels = [l for l in ["LOW", "MEDIUM", "HIGH", "CRITICAL"] if l in dist_data.index]
    ordered_values = [dist_data[l] for l in ordered_labels]
    ordered_colors = [DONUT_COLORS.get(l, "#94A3B8") for l in ordered_labels]

    fig_donut = go.Figure(data=[go.Pie(
        labels=ordered_labels,
        values=ordered_values,
        hole=0.72,
        marker=dict(
            colors=ordered_colors,
            line=dict(color='#080C14', width=4)
        ),
        textinfo='none',
        hovertemplate='<b>%{label}</b><br>%{value:,} transactions<br>%{percent}<extra></extra>',
        sort=False,
    )])

    fig_donut.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.22,
            xanchor="center", x=0.5,
            font=dict(size=12, color='#94A3B8', family='DM Sans'),
            itemsizing='constant',
            traceorder='normal',
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=30, b=110),
        height=400,
        annotations=[dict(
            text=f'<b>{total_count:,}</b><br><span style="font-size:11px;letter-spacing:0.12em">TOTAL</span>',
            x=0.5, y=0.5,
            font=dict(family='DM Sans', size=32, color='#F1F5F9'),
            showarrow=False,
            align='center',
        )]
    )

    st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# ─── LINE CHART ────────────────────────────────────────────────
with chart_right:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Alert Trend — Last 14 Days</div>', unsafe_allow_html=True)

    tmp = df.dropna(subset=["created_at"]).copy()
    tmp = tmp[tmp["final_risk_level"].isin(["HIGH", "CRITICAL"])]

    if tmp.empty:
        st.info("No high-risk alerts found")
    else:
        tmp["date"] = tmp["created_at"].dt.floor("D")
        alerts = tmp.groupby("date").size().reset_index(name="count").tail(14)

        fig_line = go.Figure()

        # Fill area
        fig_line.add_trace(go.Scatter(
            x=alerts["date"],
            y=alerts["count"],
            mode='none',
            fill='tozeroy',
            fillcolor='rgba(59,130,246,0.07)',
            showlegend=False,
            hoverinfo='skip',
        ))

        # Main line
        fig_line.add_trace(go.Scatter(
            x=alerts["date"],
            y=alerts["count"],
            mode='lines+markers',
            line=dict(color='#3B82F6', width=2.5, shape='spline', smoothing=1.2),
            marker=dict(
                color='#0A0E1A',
                size=8,
                line=dict(color='#3B82F6', width=2.5),
                symbol='circle',
            ),
            hovertemplate='<b>%{x|%b %d}</b> &nbsp; %{y:,} alerts<extra></extra>',
            showlegend=False,
        ))

        fig_line.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=10, b=40),
            height=400,
            xaxis=dict(
                showgrid=False,
                showline=False,
                color='#475569',
                tickfont=dict(size=11, family='DM Sans'),
                tickformat='%b %d',
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(148,163,184,0.06)',
                gridwidth=1,
                color='#475569',
                tickfont=dict(size=11, family='DM Sans'),
                zeroline=False,
                showline=False,
            ),
            font=dict(family='DM Sans', color='#CBD5E1'),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='#0F1825',
                font=dict(family='DM Sans', size=13, color='#F1F5F9'),
                bordercolor='rgba(59,130,246,0.35)',
                namelength=0,
            ),
        )

        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ========== OVERRIDE INSIGHTS ==========
st.markdown('<div class="section-heading">Policy Override Analysis</div>', unsafe_allow_html=True)

override_df = df[df["policy_override_applied"] == 1]

if not override_df.empty:
    oc1, oc2 = st.columns([1, 3])

    with oc1:
        st.markdown(f"""
        <div class="kpi-card kpi-purple" style="height:auto;padding:2rem 1.5rem;">
            <div class="kpi-label">Total Overrides</div>
            <div class="kpi-value">{len(override_df):,}</div>
            <div class="kpi-delta">{len(override_df)/len(df)*100:.1f}% of all transactions</div>
            <div class="kpi-glow"></div>
        </div>
        """, unsafe_allow_html=True)

    with oc2:
        all_reasons = []
        for reasons in override_df["policy_reasons"]:
            all_reasons.extend(reasons)

        if all_reasons:
            top_reasons = pd.Series(all_reasons).value_counts().head(5)
            max_count = top_reasons.iloc[0]

            st.markdown('<div class="chart-card" style="padding:1.5rem 2rem;">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title" style="margin-bottom:1.25rem;">Top Override Triggers</div>', unsafe_allow_html=True)

            for reason, count in top_reasons.items():
                pct = count / len(override_df) * 100
                bar_width = count / max_count * 100
                st.markdown(f"""
                <div class="override-row">
                    <div class="override-label">{reason}</div>
                    <div class="override-bar-wrap">
                        <div class="override-bar" style="width:{bar_width:.1f}%"></div>
                    </div>
                    <div class="override-stat">
                        <span class="override-count">{count:,}</span>
                        <span class="override-pct">{pct:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("No policy overrides detected in current dataset.")

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ========== TABLE ==========
st.markdown('<div class="section-heading">Recent Transactions</div>', unsafe_allow_html=True)

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
        "id":                       st.column_config.NumberColumn("ID",        width="small"),
        "created_at":               st.column_config.TextColumn("Timestamp",   width="medium"),
        "ml_probability":           st.column_config.NumberColumn("ML Prob",   format="%.4f", width="small"),
        "ml_risk_level":            st.column_config.TextColumn("ML Risk",     width="small"),
        "final_risk_level":         st.column_config.TextColumn("Final Risk",  width="small"),
        "final_risk_score":         st.column_config.NumberColumn("Score",     width="small"),
        "policy_override_applied":  st.column_config.CheckboxColumn("Override",width="small"),
    },
    hide_index=True,
)

# ========== FOOTER ==========
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.markdown("""
<div class="footer">
    <span class="footer-dot"></span>
    Fraud Intelligence Platform &nbsp;·&nbsp; ML + Python + Streamlit
    <span class="footer-dot"></span>
</div>
""", unsafe_allow_html=True)