import os
import pytest
import mlflow
from pathlib import Path
from src.train_pipeline import train_model

# We create a dummy csv with just 10 rows for testing
@pytest.fixture
def dummy_data_path(tmp_path):
    import pandas as pd
    import numpy as np
    
    csv_path = tmp_path / "dummy_data.csv"
    data = {
        "isFraud": [0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
        "feature1": np.random.randn(10),
        "feature2": np.random.randn(10),
        "step": range(10)
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    return csv_path

def test_train_model_logs_to_mlflow(dummy_data_path, tmp_path):
    # Set a temporary tracking URI for MLflow so we don't pollute the real one
    tracking_uri = f"sqlite:///{tmp_path}/mlflow_test.db"
    os.environ["MLFLOW_TRACKING_URI"] = tracking_uri
    mlflow.set_tracking_uri(tracking_uri)
    
    # Run training (use 10 samples to match our dummy data)
    train_model(dummy_data_path, n_samples=10)
    
    # Verify it logged
    client = mlflow.tracking.MlflowClient()
    experiments = client.search_experiments()
    assert any(e.name == "fraud_detection" for e in experiments)
    
    exp = client.get_experiment_by_name("fraud_detection")
    runs = client.search_runs(exp.experiment_id)
    assert len(runs) == 1
    
    run = runs[0]
    # Check params
    assert "n_estimators" in run.data.params
    assert run.data.params["dataset_size"] == "10"
    
    # Check metrics
    assert "roc_auc" in run.data.metrics
    assert "f1_score" in run.data.metrics
    
    # Check artifacts
    artifacts = client.list_artifacts(run.info.run_id)
    artifact_paths = [a.path for a in artifacts]
    assert "confusion_matrix.png" in artifact_paths
    
    # Check that model was registered
    versions = client.search_model_versions("name='fraud-detector-rf'")
    assert len(versions) >= 1
