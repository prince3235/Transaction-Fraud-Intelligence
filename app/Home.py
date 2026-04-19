from pathlib import Path
import sys

# Add project root to path FIRST
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.utils_dashboard import get_db_path, load_logs_df, get_total_count

DB_PATH = get_db_path(PROJECT_ROOT)

st.set_page_config(page_title="Fraud Intelligence Dashboard", layout="wide")

st.title("Transaction Fraud Intelligence System")
st.caption("End-to-end fraud detection with ML scoring, policy overrides, explainability, and alert logging.")

# ---- Load data ----
total_count = get_total_count(DB_PATH)
df = load_logs_df(DB_PATH, limit=10000)  # Load last 10k for charts (adjust as needed)

# ---- KPI row ----
c1, c2, c3, c4, c5 = st.columns(5)

critical = int((df["final_risk_level"] == "CRITICAL").sum()) if len(df) else 0
high = int((df["final_risk_level"] == "HIGH").sum()) if len(df) else 0
override_rate = float(df["policy_override_applied"].mean() * 100) if len(df) else 0.0
avg_score = float(df["final_risk_score"].mean()) if len(df) else 0.0

c1.metric("Total Scored", f"{total_count:,}")  # ✅ Real DB count
c2.metric("Critical Alerts", f"{critical:,}")
c3.metric("High Alerts", f"{high:,}")
c4.metric("Override Rate", f"{override_rate:.1f}%")

# Gauge chart for avg risk score
with c5:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_score,
        title={'text': "Avg Risk"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "lightblue"},
            'steps': [
                {'range': [0, 40], 'color': "lightgray"},
                {'range': [40, 70], 'color': "orange"},
                {'range': [70, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 85
            }
        }
    ))
    fig_gauge.update_layout(height=180, margin=dict(l=5, r=5, t=30, b=5))
    st.plotly_chart(fig_gauge, use_container_width=True)

st.divider()

if df.empty:
    st.warning("No logs found yet. First run API /predict or use the Transaction Simulator page to generate logs.")
    st.stop()

# ---- Charts row ----
left, right = st.columns([1, 1])

with left:
    st.subheader("Risk Level Distribution")
    dist = df["final_risk_level"].value_counts().reset_index()
    dist.columns = ["risk_level", "count"]
    fig = px.pie(
        dist, 
        values="count", 
        names="risk_level", 
        hole=0.55,
        color="risk_level",
        color_discrete_map={
            "LOW": "#39A0ED",
            "MEDIUM": "#F7B801",
            "HIGH": "#F18701",
            "CRITICAL": "#F35B04"
        }
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Alerts Over Time")
    tmp = df.dropna(subset=["created_at"]).copy()
    tmp = tmp[tmp["final_risk_level"].isin(["HIGH", "CRITICAL"])]
    
    if tmp.empty:
        st.info("No HIGH/CRITICAL alerts in current logs.")
    else:
        # Group by day (change to 'H' for hourly if you have realistic timestamps)
        tmp["date"] = tmp["created_at"].dt.floor("D")
        alerts = tmp.groupby("date").size().reset_index(name="alerts")
        
        fig2 = px.line(alerts, x="date", y="alerts", markers=True)
        fig2.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis_title="Date",
            yaxis_title="Alert Count"
        )
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---- Policy Override Insights ----
st.subheader("Policy Override Insights")
override_df = df[df["policy_override_applied"] == 1].copy()

if not override_df.empty:
    oc1, oc2 = st.columns(2)
    
    with oc1:
        st.metric("Overridden Transactions", f"{len(override_df):,}")
        st.caption(f"{len(override_df)/len(df)*100:.1f}% of displayed logs")
    
    with oc2:
        # Most common override reasons
        all_reasons = []
        for reasons_list in override_df["policy_reasons"]:
            all_reasons.extend(reasons_list)
        
        if all_reasons:
            reason_counts = pd.Series(all_reasons).value_counts().head(5)
            st.write("**Top Override Reasons:**")
            for reason, count in reason_counts.items():
                st.write(f"- {reason} ({count})")
else:
    st.info("No policy overrides in current logs.")

st.divider()

# ---- Recent Transactions Table ----
st.subheader("Recent Transactions (latest 50)")
show_cols = [
    "id", "created_at", "ml_probability", "ml_risk_level",
    "final_risk_level", "final_risk_score", "policy_override_applied"
]

display_df = df[show_cols].head(50).copy()
display_df["ml_probability"] = display_df["ml_probability"].round(4)
display_df["created_at"] = display_df["created_at"].dt.strftime("%Y-%m-%d %H:%M")

st.dataframe(
    display_df,
    use_container_width=True,
    column_config={
        "final_risk_level": st.column_config.TextColumn(
            "Final Risk",
            help="Risk level after policy overrides"
        ),
        "policy_override_applied": st.column_config.CheckboxColumn(
            "Override?",
            help="Policy rules triggered"
        )
    }
)