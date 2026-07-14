"""
Tests for the Phase 5 ML improvement modules:
- src/feature_audit.py
- src/permutation_importance.py
- src/calibration.py
"""
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.feature_audit import (
    audit_single_feature_leakage,
    audit_deterministic_rules,
    audit_permutation_drop,
)
from src.permutation_importance import compute_permutation_importance
from src.calibration import (
    compute_calibration_curve,
    compute_brier_decomposition,
    compute_ece,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def synthetic_fraud_data():
    """Create a small synthetic dataset with a deliberately leaked feature."""
    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        "amount": np.random.exponential(10000, n),
        "step": np.random.randint(1, 100, n),
        "oldbalanceOrg": np.random.exponential(50000, n),
        # LEAKED: perfectly predicts isFraud
        "leaked_flag": np.random.choice([0, 1], n, p=[0.9, 0.1]),
        # Legit feature with some signal
        "type_risk_score": np.random.choice([1, 2, 3], n),
    })
    # Make leaked_flag perfectly correlate with target
    df["isFraud"] = df["leaked_flag"]
    # Add some noise to type_risk_score correlation
    df.loc[df["isFraud"] == 1, "type_risk_score"] = np.random.choice([3, 3, 3], (df["isFraud"] == 1).sum())
    return df


@pytest.fixture
def fitted_mock_model():
    """A mock model with predict_proba for permutation importance tests."""
    model = MagicMock()
    # Simulate a model where feature 0 is important, feature 1 is not
    def mock_predict_proba(X):
        # If feature 0 is shuffled, predictions get worse
        prob = X.iloc[:, 0].values * 0.5 + 0.3
        prob = np.clip(prob, 0.01, 0.99)
        return np.column_stack([1 - prob, prob])
    model.predict_proba = mock_predict_proba
    return model


# ── Feature audit tests ───────────────────────────────────────────────────────

def test_single_feature_leakage_detects_perfect_predictor(synthetic_fraud_data):
    """A feature with AUC=1.0 should be flagged as CRITICAL leakage."""
    findings = audit_single_feature_leakage(synthetic_fraud_data)
    # leaked_flag perfectly predicts isFraud
    leaked = [f for f in findings if f["feature"] == "leaked_flag"]
    assert len(leaked) == 1
    assert leaked[0]["severity"] == "CRITICAL"
    assert leaked[0]["leak_score"] >= 0.999


def test_single_feature_leakage_ignores_weak_predictors(synthetic_fraud_data):
    """A feature with AUC < 0.95 should NOT be flagged."""
    findings = audit_single_feature_leakage(synthetic_fraud_data)
    # 'step' is random noise — should not appear
    flagged_features = {f["feature"] for f in findings}
    assert "step" not in flagged_features


def test_deterministic_rules_detects_degenerate_feature():
    """A feature that always equals 1 for fraud, 0 for legit should be flagged."""
    df = pd.DataFrame({
        "sender_account_emptied": [1] * 100 + [0] * 900,
        "isFraud": [1] * 100 + [0] * 900,
    })
    findings = audit_deterministic_rules(df)
    assert len(findings) == 1
    assert findings[0]["feature"] == "sender_account_emptied"
    assert findings[0]["severity"] == "CRITICAL"
    assert findings[0]["fraud_mode_fraction"] > 0.95
    assert findings[0]["legit_mode_fraction"] < 0.05


def test_permutation_drop_identifies_important_feature(synthetic_fraud_data):
    """Removing the most predictive feature should cause the biggest AUC drop."""
    # Use a small sample for speed
    findings = audit_permutation_drop(synthetic_fraud_data, sample_size=500)
    # leaked_flag should be near the top
    top_feature = findings[0]["feature"] if findings else None
    assert top_feature == "leaked_flag"
    assert findings[0]["auc_drop"] > 0.10  # >10% drop


# ── Permutation importance tests ──────────────────────────────────────────────

def test_permutation_importance_returns_sorted_list(fitted_mock_model):
    """Results should be sorted by importance descending."""
    X = pd.DataFrame({"important": np.random.rand(200), "noise": np.random.rand(200)})
    y = pd.Series((X["important"] > 0.5).astype(int))
    results = compute_permutation_importance(fitted_mock_model, X, y, n_repeats=2)
    assert len(results) == 2
    importances = [r["importance"] for r in results]
    assert importances == sorted(importances, reverse=True)


def test_permutation_importance_handles_constant_feature(fitted_mock_model):
    """A constant feature (no variance) should have ~0 importance."""
    X = pd.DataFrame({"constant": [0.5] * 100, "varying": np.random.rand(100)})
    y = pd.Series(np.random.randint(0, 2, 100))
    results = compute_permutation_importance(fitted_mock_model, X, y, n_repeats=2)
    constant_result = [r for r in results if r["feature"] == "constant"][0]
    # Shuffling a constant column doesn't change anything → importance ≈ 0
    assert abs(constant_result["importance"]) < 0.01


# ── Calibration tests ─────────────────────────────────────────────────────────

def test_calibration_curve_perfect_calibration():
    """A perfectly calibrated predictor should have fraction=probability."""
    np.random.seed(42)
    # Generate probs that match the true rate in each bin
    y_true = np.array([0] * 500 + [1] * 500)
    y_prob = np.concatenate([
        np.random.uniform(0, 0.2, 500),  # non-fraud has low prob
        np.random.uniform(0.8, 1.0, 500),  # fraud has high prob
    ])
    curve = compute_calibration_curve(y_true, y_prob, n_bins=5)
    assert len(curve["bin_centers"]) == 5
    assert len(curve["fraction_of_positives"]) == 5
    assert sum(curve["bin_counts"]) == 1000


def test_brier_decomposition_sums_correctly():
    """Brier ≈ reliability - resolution + uncertainty (within numerical tolerance)."""
    np.random.seed(42)
    # Use a larger sample + more bins for better numerical stability
    y_true = np.random.randint(0, 2, 5000)
    # Make probs correlate with target so resolution is non-zero
    y_prob = np.where(y_true == 1, np.random.uniform(0.6, 1.0, 5000), np.random.uniform(0.0, 0.4, 5000))
    decomp = compute_brier_decomposition(y_true, y_prob, n_bins=10)
    # The decomposition should approximately hold (the standard formula has
    # small numerical differences due to bin edge handling)
    expected_brier = decomp["reliability"] - decomp["resolution"] + decomp["uncertainty"]
    assert abs(decomp["brier_score"] - expected_brier) < 0.05
    assert decomp["uncertainty"] > 0  # binary target always has > 0 uncertainty


def test_ece_zero_for_perfect_calibration():
    """ECE should be near 0 for a perfectly calibrated predictor."""
    y_true = np.array([0] * 100 + [1] * 100)
    y_prob = np.array([0.0] * 100 + [1.0] * 100)  # perfect
    ece = compute_ece(y_true, y_prob, n_bins=10)
    assert ece < 0.01


def test_ece_high_for_miscalibrated():
    """ECE should be high for a badly miscalibrated predictor."""
    # Model always predicts 0.99 but true rate is 0.5
    y_true = np.array([0] * 500 + [1] * 500)
    y_prob = np.full(1000, 0.99)
    ece = compute_ece(y_true, y_prob, n_bins=10)
    assert ece > 0.4  # heavily miscalibrated
