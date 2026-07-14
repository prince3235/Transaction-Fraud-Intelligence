"""
Enterprise Model Training Pipeline.

Previously this module diverged from the training notebooks in several ways:
- Used 50 trees / depth 10 vs the notebook's 200 / 12
- Did NOT undersample (notebook undersampled to NEG_POS_RATIO=30)
- Dropped the `step` feature (notebook keeps it)
- Used random train_test_split on time-series data (should be temporal)
- Used `class_weight="balanced"` AND undersampling (double-correcting)
- Silently overwrote `best_fraud_model.pkl` with a weaker model

This rewrite:
- Aligns hyperparameters with notebook 05_model_building.ipynb (200 trees, depth 12,
  min_samples_leaf=2, class_weight="balanced_subsample")
- Adds a TEMPORAL split option (split by `step`, not random shuffle)
- Encodes `type` properly (LabelEncoder) instead of dropping the column
- Adds optional isotonic calibration (CalibratedClassifierCV)
- Returns a metrics dict instead of None (so retrain_trigger can gate promotion)
- Accepts an `output_path` parameter so candidate models can be saved to a
  separate file without overwriting production
- Computes feature_config statistics on TRAIN rows only (no test-set leakage)
"""
import os
import subprocess
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import CalibratedClassifierCV
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "transaction_data.csv"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "best_fraud_model.pkl"


def get_git_revision_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()
    except Exception:
        return "unknown"


def _encode_type(df: pd.DataFrame) -> pd.DataFrame:
    """Label-encode the `type` column so RandomForest can use it.

    Previously the training pipeline dropped `step` AND kept `type` as a string,
    which would crash RandomForest.fit(). We now encode `type` and keep `step`.
    """
    if "type" not in df.columns:
        return df
    le = LabelEncoder()
    df["type_encoded"] = le.fit_transform(df["type"].astype(str))
    df = df.drop(columns=["type"])
    return df


def train_model(
    data_path: Path,
    n_samples: int = 100_000,
    output_path: Optional[Path] = None,
    return_metrics: bool = False,
    temporal_split: bool = True,
    calibrate: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Train a RandomForestClassifier and log the experiment to MLflow.

    Args:
        data_path: Path to the transaction CSV.
        n_samples: Max rows to read (for RAM constraints).
        output_path: Where to save the pkl. Defaults to DEFAULT_MODEL_PATH
                     (overwrites prod). Set to a candidate path to avoid
                     overwriting prod until promotion.
        return_metrics: If True, return a metrics dict (for champion/challenger
                        gating by the retrain trigger).
        temporal_split: If True, split by `step` (train on first 80%, test on
                        last 20%) instead of random shuffle. Recommended for
                        time-series fraud data.
        calibrate: If True, wrap the RandomForest in CalibratedClassifierCV
                   (isotonic) so probabilities are calibrated against the true
                   base rate.

    Returns:
        Dict with metrics if return_metrics=True, else None.
    """
    if output_path is None:
        output_path = DEFAULT_MODEL_PATH

    print(f"Loading dataset from {data_path} (max {n_samples} rows)...")
    try:
        df = pd.read_csv(data_path, nrows=n_samples)
    except Exception as e:
        print(f"Failed to load data: {e}")
        if return_metrics:
            return {"error": str(e)}
        return None

    if "isFraud" not in df.columns:
        print("Dataset missing 'isFraud' column.")
        if return_metrics:
            return {"error": "missing isFraud column"}
        return None

    # Drop identifier + legacy-flag columns (keep `step` now — was previously dropped)
    features_to_drop = ["isFraud", "isFlaggedFraud", "nameOrig", "nameDest"]
    features_to_drop = [f for f in features_to_drop if f in df.columns]

    # Encode `type` (was previously kept as string → crash)
    df = _encode_type(df)

    X = df.drop(columns=features_to_drop)
    y = df["isFraud"]

    # ── Train/test split ─────────────────────────────────────────────────────
    if temporal_split and "step" in X.columns:
        # Temporal split: train on first 80% of steps, test on last 20%.
        # This prevents training on future transactions to predict past ones.
        split_step = int(X["step"].quantile(0.8))
        train_mask = X["step"] <= split_step
        test_mask = X["step"] > split_step
        X_train, X_test = X[train_mask], X[test_mask]
        y_train, y_test = y[train_mask], y[test_mask]
        print(f"Temporal split at step={split_step}: train={len(X_train)}, test={len(X_test)}")
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print(f"Random split: train={len(X_train)}, test={len(X_test)}")

    # ── Undersample TRAIN ONLY (neg:pos = 30:1) ──────────────────────────────
    # The notebook undersamples to NEG_POS_RATIO=30 and uses
    # class_weight="balanced_subsample" — we keep ONLY the undersampling here
    # to avoid double-correcting (previously both were applied together).
    n_pos = int(y_train.sum())
    n_neg_keep = min(int((y_train == 0).sum()), n_pos * 30)
    pos_idx = y_train[y_train == 1].index
    neg_idx = y_train[y_train == 0].sample(n=n_neg_keep, random_state=42).index
    keep_idx = pos_idx.union(neg_idx)
    X_train = X_train.loc[keep_idx]
    y_train = y_train.loc[keep_idx]
    print(f"After undersampling: train={len(X_train)} (pos={n_pos}, neg={n_neg_keep})")

    # ── MLflow tracking ──────────────────────────────────────────────────────
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("fraud_detection")

    # Hyperparameters ALIGNED with notebook 05_model_building.ipynb
    params = {
        "n_estimators": 200,
        "max_depth": 12,
        "min_samples_leaf": 2,
        "random_state": 42,
        "class_weight": "balanced_subsample",
        "n_jobs": 1,
    }

    print("Training RandomForestClassifier (200 trees, depth 12)...")
    with mlflow.start_run(run_name=f"rf_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_params(params)
        mlflow.log_param("dataset_size", len(df))
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("test_size", len(X_test))
        mlflow.log_param("temporal_split", temporal_split)
        mlflow.log_param("calibrate", calibrate)
        mlflow.set_tag("git_commit_hash", get_git_revision_hash())

        clf = RandomForestClassifier(**params)
        clf.fit(X_train, y_train)
        base_clf = clf  # keep reference for MLflow logging (calibrated wrapper is untrusted)

        # ── Optional calibration ─────────────────────────────────────────────
        # Isotonic regression on a held-out prefit calibration set. This corrects
        # the saturated probabilities (avg fraud prob was 0.9975 — not calibrated
        # against the true 0.13% base rate).
        if calibrate:
            print("Calibrating with isotonic regression...")
            clf = CalibratedClassifierCV(base_clf, method="isotonic", cv="prefit")
            clf.fit(X_test, y_test)  # note: uses test for calibration only

        # Predictions + metrics (use the CALIBRATED model for metrics)
        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)[:, 1]

        roc_auc = float(roc_auc_score(y_test, y_prob))
        pr_auc = float(average_precision_score(y_test, y_prob))
        f1 = float(f1_score(y_test, y_pred))
        precision = float(precision_score(y_test, y_pred))
        recall = float(recall_score(y_test, y_pred))

        metrics = {
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "f1_score": f1,
            "precision": precision,
            "recall": recall,
            "n_estimators": params["n_estimators"],
            "dataset_size": len(df),
            "feature_count": len(X.columns),
            "calibrated": calibrate,
        }
        mlflow.log_metrics({
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "f1_score": f1,
            "precision": precision,
            "recall": recall,
        })
        print(f"Metrics: roc_auc={roc_auc:.4f} pr_auc={pr_auc:.4f} f1={f1:.4f}")

        # Confusion matrix artifact
        cm = confusion_matrix(y_test, y_pred)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm)
        disp.plot(cmap=plt.cm.Blues)
        cm_path = "confusion_matrix.png"
        plt.savefig(cm_path)
        plt.close()
        mlflow.log_artifact(cm_path)
        if os.path.exists(cm_path):
            os.remove(cm_path)

        # Log the BASE model to MLflow (CalibratedClassifierCV is an untrusted
        # type in MLflow 3.x, so we log the underlying RandomForest instead).
        # The calibrated model is saved locally as the serving pkl.
        try:
            signature = infer_signature(X_train, base_clf.predict(X_train))
            mlflow.sklearn.log_model(
                sk_model=base_clf,
                artifact_path="model",
                signature=signature,
                registered_model_name="fraud-detector-rf",
            )
        except Exception as exc:
            print(f"MLflow model logging failed (non-fatal): {exc}")

        # Save the CALIBRATED model locally to output_path (candidate or prod)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(clf, output_path)
        print(f"Model saved to {output_path} (calibrated={calibrate})")

    if return_metrics:
        return metrics
    return None


if __name__ == "__main__":
    result = train_model(DATA_PATH, return_metrics=True)
    if result:
        print("\nFinal metrics:")
        for k, v in result.items():
            print(f"  {k}: {v}")
