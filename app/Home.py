from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from app.utils_dashboard import get_db_path, load_logs_df, get_total_count
from app.styles import inject_custom_css

# Page config
st.set_page_config(
    page_title="Fraud Intelligence Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS
inject_custom_css()

# Load data
DB_PATH = get_db_path(PROJECT_ROOT)
total_count = get_total_count(DB_PATH)
df = load_logs_df(DB_PATH, limit=10000)

# ========== HEADER ==========
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("🛡️ Transaction Fraud Intelligence")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with col_refresh:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

st.markdown("---")

# ========== METRICS ROW ==========
if df.empty:
    st.warning("⚠️ No logs found. Generate sample data using `/admin/seed-logs` API endpoint.")
    st.stop()

critical = int((df["final_risk_level"] == "CRITICAL").sum())
high = int((df["final_risk_level"] == "HIGH").sum())
override_rate = float(df["policy_override_applied"].mean() * 100)
avg_score = float(df["final_risk_score"].mean())

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric(
        label="Total Scored",
        value=f"{total_count:,}",
        delta="All time"
    )

with m2:
    st.metric(
        label="Critical Alerts",
        value=f"{critical:,}",
        delta=f"{critical/total_count*100:.1f}%" if total_count else "0%"
    )

with m3:
    st.metric(
        label="High Alerts",
        value=f"{high:,}",
        delta=f"{high/total_count*100:.1f}%" if total_count else "0%"
    )

with m4:
    st.metric(
        label="Override Rate",
        value=f"{override_rate:.1f}%",
        delta="Policy triggers"
    )

with m5:
    # Gauge chart for avg score
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_score,
        title={'text': "Avg Risk", 'font': {'size': 14, 'color': '#94a3b8'}},
        number={'font': {'size': 28, 'color': 'white'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#475569'},
            'bar': {'color': '#3b82f6', 'thickness': 0.7},
            'bgcolor': 'rgba(255,255,255,0.05)',
            'borderwidth': 2,
            'bordercolor': 'rgba(255,255,255,0.1)',
            'steps': [
                {'range': [0, 40], 'color': 'rgba(16, 185, 129, 0.2)'},
                {'range': [40, 70], 'color': 'rgba(245, 158, 11, 0.2)'},
                {'range': [70, 100], 'color': 'rgba(239, 68, 68, 0.2)'}
            ],
            'threshold': {
                'line': {'color': 'red', 'width': 3},
                'thickness': 0.75,
                'value': 85
            }
        }
    ))
    
    fig_gauge.update_layout(
        height=180,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'}
    )
    
    st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("---")

# ========== CHARTS ROW ==========
chart1, chart2 = st.columns(2)

with chart1:
    st.subheader("📊 Risk Distribution")
    
    dist = df["final_risk_level"].value_counts().reset_index()
    dist.columns = ["risk_level", "count"]
    
    color_map = {
        "LOW": "#10b981",
        "MEDIUM": "#f59e0b",
        "HIGH": "#f97316",
        "CRITICAL": "#ef4444"
    }
    
    fig_pie = px.pie(
        dist,
        values="count",
        names="risk_level",
        hole=0.5,
        color="risk_level",
        color_discrete_map=color_map
    )
    
    fig_pie.update_traces(
        textposition='inside',
        textinfo='label+percent',
        textfont_size=12,
        marker=dict(line=dict(color='#0f172a', width=2))
    )
    
    fig_pie.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(color='white')
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=350,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

with chart2:
    st.subheader("📈 Alerts Over Time")
    
    tmp = df.dropna(subset=["created_at"]).copy()
    tmp = tmp[tmp["final_risk_level"].isin(["HIGH", "CRITICAL"])]
    
    if tmp.empty:
        st.info("No HIGH/CRITICAL alerts in current logs")
    else:
        tmp["date"] = tmp["created_at"].dt.floor("D")
        alerts = tmp.groupby("date").size().reset_index(name="alerts")
        
        fig_line = px.line(
            alerts,
            x="date",
            y="alerts",
            markers=True,
            template="plotly_dark"
        )
        
        fig_line.update_traces(
            line_color='#ef4444',
            line_width=3,
            marker=dict(size=8, color='#ef4444')
        )
        
        fig_line.update_layout(
            xaxis_title="Date",
            yaxis_title="Alert Count",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(255,255,255,0.02)',
            font=dict(color='white'),
            height=350,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
        )
        
        st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

# ========== OVERRIDE INSIGHTS ==========
st.subheader("⚡ Policy Override Insights")

override_df = df[df["policy_override_applied"] == 1].copy()

if not override_df.empty:
    oc1, oc2 = st.columns([1, 2])
    
    with oc1:
        st.metric(
            "Overridden Transactions",
            f"{len(override_df):,}",
            delta=f"{len(override_df)/len(df)*100:.1f}% of total"
        )
    
    with oc2:
        all_reasons = []
        for reasons_list in override_df["policy_reasons"]:
            all_reasons.extend(reasons_list)
        
        if all_reasons:
            reason_counts = pd.Series(all_reasons).value_counts().head(5)
            
            st.markdown("**Top Override Reasons:**")
            for reason, count in reason_counts.items():
                pct = count / len(override_df) * 100
                st.markdown(f"""
                <div style="margin: 0.5rem 0;">
                    <span class="badge badge-high">{count}</span>
                    <span style="color: #e2e8f0; margin-left: 0.5rem;">{reason}</span>
                    <span style="color: #94a3b8; margin-left: 0.5rem;">({pct:.1f}%)</span>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("No policy overrides in current logs")

st.markdown("---")

# ========== TRANSACTIONS TABLE ==========
st.subheader("📋 Recent Transactions")

show_cols = [
    "id", "created_at", "ml_probability", "ml_risk_level",
    "final_risk_level", "final_risk_score", "policy_override_applied"
]

display_df = df[show_cols].head(50).copy()
display_df["ml_probability"] = display_df["ml_probability"].round(4)
display_df["created_at"] = display_df["created_at"].dt.strftime("%Y-%m-%d %H:%M")

# Add color-coded risk badges
def risk_badge(level):
    badges = {
        "LOW": "badge-low",
        "MEDIUM": "badge-medium",
        "HIGH": "badge-high",
        "CRITICAL": "badge-critical"
    }
    return f'<span class="badge {badges.get(level, "badge-low")}">{level}</span>'

st.dataframe(
    display_df,
    use_container_width=True,
    column_config={
        "created_at": st.column_config.TextColumn("Timestamp"),
        "ml_probability": st.column_config.NumberColumn("ML Prob", format="%.4f"),
        "final_risk_level": st.column_config.TextColumn("Final Risk"),
        "final_risk_score": st.column_config.NumberColumn("Score", format="%d"),
        "policy_override_applied": st.column_config.CheckboxColumn("Override?")
    },
    hide_index=True
)

# Footer
st.markdown("---")
st.caption("🛡️ Transaction Fraud Intelligence System | Built with Streamlit + Python + ML")