from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # pages folder ke liye parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path
import streamlit as st
import plotly.express as px

from app.utils_dashboard import get_db_path, load_logs_df

import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = get_db_path(PROJECT_ROOT)

st.set_page_config(page_title="Alerts Monitoring", layout="wide")
st.title("Alerts Monitoring")
st.caption("Filter, inspect, and review high-risk transactions from SQLite logs.")

df = load_logs_df(DB_PATH, limit=10000)

if df.empty:
    st.warning("No logs found. Generate some logs via API /predict or Transaction Simulator.")
    st.stop()

# Filters
col1, col2, col3 = st.columns(3)
risk_filter = col1.multiselect("Risk Levels", ["LOW","MEDIUM","HIGH","CRITICAL"], default=["HIGH","CRITICAL"])
min_score = col2.slider("Min Risk Score", 0, 100, 70)
only_override = col3.checkbox("Only Policy Overrides", value=False)

f = df[df["final_risk_level"].isin(risk_filter)]
f = f[f["final_risk_score"] >= min_score]
if only_override:
    f = f[f["policy_override_applied"] == 1]

st.subheader("Alert Queue")
st.dataframe(
    f[["id","created_at","final_risk_level","final_risk_score","ml_probability","policy_override_applied","suspicious_signal_count"]].head(200),
    use_container_width=True
)

st.divider()
st.subheader("Alert Details")

ids = f["id"].head(500).tolist()
selected_id = st.selectbox("Select log id", ids)

row = f[f["id"] == selected_id].iloc[0]
st.write("Final Risk:", row["final_risk_level"], "| Score:", int(row["final_risk_score"]))
st.write("ML Probability:", float(row["ml_probability"]), "| ML Level:", row["ml_risk_level"])

st.markdown("### Policy Reasons")
st.write(row["policy_reasons"])

st.markdown("### Transaction Input")
st.json(row["transaction"])

st.markdown("### Alert Object")
st.json(row["alert"])