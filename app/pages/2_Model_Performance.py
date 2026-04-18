from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # pages folder ke liye parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    confusion_matrix, precision_score, recall_score, f1_score
)

st.set_page_config(page_title="Model Performance", layout="wide")
st.title("Model Performance")
st.caption("Evaluate ML scoring performance on the test set (imbalanced metrics: PR-AUC/Recall).")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

y_test_path = PROJECT_ROOT / "data" / "processed" / "y_test.csv"
prob_path = PROJECT_ROOT / "data" / "processed" / "best_model_probs.npy"

y_test = pd.read_csv(y_test_path).squeeze()
y_prob = np.load(prob_path)

roc = roc_auc_score(y_test, y_prob)
pr  = average_precision_score(y_test, y_prob)

c1, c2 = st.columns(2)
c1.metric("ROC-AUC", f"{roc:.4f}")
c2.metric("PR-AUC", f"{pr:.4f}")

thr = st.slider("Decision Threshold", 0.05, 0.95, 0.50, 0.01)
y_pred = (y_prob >= thr).astype(int)

prec = precision_score(y_test, y_pred, zero_division=0)
rec  = recall_score(y_test, y_pred, zero_division=0)
f1   = f1_score(y_test, y_pred, zero_division=0)

m1, m2, m3 = st.columns(3)
m1.metric("Precision (Fraud)", f"{prec:.4f}")
m2.metric("Recall (Fraud)", f"{rec:.4f}")
m3.metric("F1", f"{f1:.4f}")

cm = confusion_matrix(y_test, y_pred)
cm_df = pd.DataFrame(cm, index=["Actual 0","Actual 1"], columns=["Pred 0","Pred 1"])

st.subheader("Confusion Matrix")
fig = px.imshow(cm_df, text_auto=True, color_continuous_scale="Blues")
fig.update_layout(height=380)
st.plotly_chart(fig, use_container_width=True)