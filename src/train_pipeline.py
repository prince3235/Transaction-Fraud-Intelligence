import os
import subprocess
import warnings
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
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
    ConfusionMatrixDisplay
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature

warnings.filterwarnings('ignore')

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "transaction_data.csv"
LOCAL_MODEL_PATH = PROJECT_ROOT / "models" / "best_fraud_model.pkl"

def get_git_revision_hash() -> str:
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
    except Exception:
        return "unknown"

def train_model(data_path: Path, n_samples: int = 100000):
    """
    Train a RandomForestClassifier and log the experiment to MLflow.
    We sample the dataset to stay within 8GB RAM constraints.
    """
    print(f"Loading dataset from {data_path}...")
    # Read a sample to save RAM (adjust if needed)
    try:
        # Load a random sample of the data. 
        # For simplicity and speed in this constraint environment, we take the first `n_samples` rows,
        # but in production you'd use a better sampling technique.
        df = pd.read_csv(data_path, nrows=n_samples)
    except Exception as e:
        print(f"Failed to load data: {e}")
        return
    
    if "isFraud" not in df.columns:
        print("Dataset missing 'isFraud' column.")
        return

    # Keep a subset of features to mimic existing model
    features_to_drop = ["isFraud", "isFlaggedFraud", "step", "nameOrig", "nameDest"]
    features_to_drop = [f for f in features_to_drop if f in df.columns]
    
    X = df.drop(columns=features_to_drop)
    y = df["isFraud"]

    # Basic train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # If the user has a tracking URI set (e.g. from docker-compose), use it.
    # Otherwise, fallback to local mlruns.
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(tracking_uri)
    
    mlflow.set_experiment("fraud_detection")

    print("Starting MLflow run...")
    with mlflow.start_run(run_name=f"rf_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        
        # Hyperparameters
        params = {
            "n_estimators": 50,
            "max_depth": 10,
            "random_state": 42,
            "class_weight": "balanced",
            "n_jobs": 1 # Keep low for RAM/CPU constraints
        }
        
        # Log params
        mlflow.log_params(params)
        mlflow.log_param("dataset_size", len(df))
        
        # Tag commit hash
        commit_hash = get_git_revision_hash()
        mlflow.set_tag("git_commit_hash", commit_hash)

        print("Training RandomForestClassifier...")
        clf = RandomForestClassifier(**params)
        clf.fit(X_train, y_train)

        # Predictions
        y_pred = clf.predict(X_test)
        y_prob = clf.predict_proba(X_test)[:, 1]

        # Metrics
        roc_auc = roc_auc_score(y_test, y_prob)
        pr_auc = average_precision_score(y_test, y_prob)
        f1 = f1_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)

        metrics = {
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "f1_score": f1,
            "precision": precision,
            "recall": recall
        }
        mlflow.log_metrics(metrics)
        print(f"Metrics: {metrics}")

        # Confusion Matrix Artifact
        cm = confusion_matrix(y_test, y_pred)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm)
        disp.plot(cmap=plt.cm.Blues)
        
        cm_path = "confusion_matrix.png"
        plt.savefig(cm_path)
        plt.close()
        mlflow.log_artifact(cm_path)
        if os.path.exists(cm_path):
            os.remove(cm_path)

        # Infer signature
        signature = infer_signature(X_train, y_pred)

        # Log Model
        print("Logging model to MLflow...")
        mlflow.sklearn.log_model(
            sk_model=clf,
            artifact_path="model",
            signature=signature,
            registered_model_name="fraud-detector-rf"
        )
        
        # Also save locally as a fallback for api/main.py if MLflow is down
        LOCAL_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(clf, LOCAL_MODEL_PATH)
        print(f"Model saved locally to {LOCAL_MODEL_PATH}")

if __name__ == "__main__":
    train_model(DATA_PATH)
