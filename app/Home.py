from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app.utils_dashboard import get_db_path, load_logs_df

# ensure src imports always work
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = get_db_path(PROJECT_ROOT)

st.set_page_config(page_title="Fraud Intelligence Dashboard", layout="wide")

st.title("Transaction Fraud Intelligence System")
st.caption("End-to-end fraud detection with ML scoring, policy overrides, explainability, and alert logging.")

df = load_logs_df(DB_PATH, limit=5000)

# ---- KPI row ----
c1, c2, c3, c4, c5 = st.columns(5)

total = len(df)
critical = int((df["final_risk_level"] == "CRITICAL").sum()) if total else 0
high = int((df["final_risk_level"] == "HIGH").sum()) if total else 0
override_rate = float(df["policy_override_applied"].mean() * 100) if total else 0.0
avg_score = float(df["final_risk_score"].mean()) if total else 0.0

c1.metric("Total Scored", f"{total}")
c2.metric("Critical Alerts", f"{critical}")
c3.metric("High Alerts", f"{high}")
c4.metric("Override Rate", f"{override_rate:.1f}%")
c5.metric("Avg Risk Score", f"{avg_score:.1f}")

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
    fig = px.pie(dist, values="count", names="risk_level", hole=0.55,
                 color="risk_level",
                 color_discrete_map={"LOW":"#39A0ED","MEDIUM":"#F7B801","HIGH":"#F18701","CRITICAL":"#F35B04"})
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Alerts Over Time (last logs)")
    tmp = df.dropna(subset=["created_at"]).copy()
    tmp = tmp.sort_values("created_at")
    tmp["date"] = tmp["created_at"].dt.floor("H")
    alerts = tmp[tmp["final_risk_level"].isin(["HIGH", "CRITICAL"])].groupby("date").size().reset_index(name="alerts")
    if alerts.empty:
        st.info("No HIGH/CRITICAL alerts in current logs.")
    else:
        fig2 = px.line(alerts, x="date", y="alerts", markers=True)
        fig2.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

st.subheader("Recent Transactions (latest 50)")
show_cols = ["id", "created_at", "ml_probability", "ml_risk_level", "final_risk_level", "final_risk_score", "policy_override_applied", "suspicious_signal_count"]
st.dataframe(df[show_cols].head(50), use_container_width=True)