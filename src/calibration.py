"""
Model Calibration Module.

Provides:
1. Calibration curve generation (reliability diagram data)
2. Brier score decomposition (reliability, resolution, uncertainty)
3. Expected Calibration Error (ECE)
4. Comparison of uncalibrated vs isotonic vs Platt calibration

The Phase 4 audit found that the production model has saturated probabilities
(avg fraud prob = 0.9975, avg non-fraud prob = 0.00064) — the model is
essentially a binary oracle, not a calibrated risk scorer. This module
quantifies that miscalibration and helps choose the right calibration method.

Usage:
    python -m src.calibration --data-path data/processed/ --model models/best_fraud_model.pkl
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import brier_score_loss, roc_auc_score, average_precision_score

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_calibration_curve(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10, strategy: str = "quantile"
) -> Dict[str, Any]:
    """
    Compute calibration curve (reliability diagram) data.

    Args:
        y_true: Binary true labels (0/1)
        y_prob: Predicted probabilities
        n_bins: Number of bins (default 10)
        strategy: 'quantile' (equal-frequency) or 'uniform' (equal-width)

    Returns:
        Dict with:
        - bin_centers: midpoint probability of each bin
        - fraction_of_positives: observed fraud rate in each bin
        - bin_counts: number of samples in each bin
        - n_bins: number of bins
        - strategy: binning strategy used
    """
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy=strategy)

    # Compute bin counts
    if strategy == "quantile":
        bins = np.percentile(y_prob, np.linspace(0, 100, n_bins + 1))
    else:
        bins = np.linspace(0, 1, n_bins + 1)
    bins[0] = -np.inf
    bins[-1] = np.inf
    bin_counts = np.histogram(y_prob, bins=bins)[0]

    return {
        "bin_centers": prob_pred.tolist(),
        "fraction_of_positives": prob_true.tolist(),
        "bin_counts": bin_counts.tolist(),
        "n_bins": n_bins,
        "strategy": strategy,
    }


def compute_brier_decomposition(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> Dict[str, float]:
    """
    Decompose the Brier score into reliability, resolution, and uncertainty.

    Brier = RELIABILITY - RESOLUTION + UNCERTAINTY

    - RELIABILITY: how well-calibrated the predictions are (lower = better)
    - RESOLUTION: how much the predictions vary across bins (higher = better)
    - UNCERTAINTY: inherent variance of the target (irreducible)

    A well-calibrated model has low reliability and high resolution.
    """
    bins = np.percentile(y_prob, np.linspace(0, 100, n_bins + 1))
    bins[0] = -np.inf
    bins[-1] = np.inf
    bin_indices = np.digitize(y_prob, bins[1:-1])

    reliability = 0.0
    resolution = 0.0
    n_total = len(y_true)
    base_rate = y_true.mean()

    for b in range(n_bins):
        mask = bin_indices == b
        n_b = mask.sum()
        if n_b == 0:
            continue
        obs_rate = y_true[mask].mean()
        pred_mean = y_prob[mask].mean()
        reliability += n_b * (obs_rate - pred_mean) ** 2
        resolution += n_b * (obs_rate - base_rate) ** 2

    reliability /= n_total
    resolution /= n_total
    uncertainty = base_rate * (1 - base_rate)
    brier = brier_score_loss(y_true, y_prob)

    return {
        "brier_score": float(brier),
        "reliability": float(reliability),
        "resolution": float(resolution),
        "uncertainty": float(uncertainty),
    }


def compute_ece(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> float:
    """
    Expected Calibration Error (ECE).

    Weighted average of |accuracy - confidence| across bins. Lower = better
    calibrated. A perfectly calibrated model has ECE = 0.
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(y_prob, bins[1:-1])

    ece = 0.0
    n_total = len(y_true)

    for b in range(n_bins):
        mask = bin_indices == b
        n_b = mask.sum()
        if n_b == 0:
            continue
        acc = y_true[mask].mean()
        conf = y_prob[mask].mean()
        ece += (n_b / n_total) * abs(acc - conf)

    return float(ece)


def compare_calibration_methods(
    model,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_calib: pd.DataFrame,
    y_calib: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Dict[str, Any]:
    """
    Compare uncalibrated vs Platt (sigmoid) vs isotonic calibration.

    Trains each calibration method on (X_calib, y_calib), evaluates on
    (X_test, y_test), and returns metrics + calibration curve data.

    The base model must already be fitted on (X_train, y_train).
    """
    methods: Dict[str, Any] = {}

    # 1. Uncalibrated baseline
    y_prob_uncal = model.predict_proba(X_test)[:, 1]
    methods["uncalibrated"] = {
        "roc_auc": float(roc_auc_score(y_test, y_prob_uncal)),
        "pr_auc": float(average_precision_score(y_test, y_prob_uncal)),
        "brier": float(brier_score_loss(y_test, y_prob_uncal)),
        "ece": compute_ece(y_test.values, y_prob_uncal),
        "mean_pred_prob": float(y_prob_uncal.mean()),
        "calibration_curve": compute_calibration_curve(y_test.values, y_prob_uncal),
        "brier_decomposition": compute_brier_decomposition(y_test.values, y_prob_uncal),
    }

    # 2. Platt (sigmoid) calibration
    try:
        platt = CalibratedClassifierCV(model, method="sigmoid", cv="prefit")
        platt.fit(X_calib, y_calib)
        y_prob_platt = platt.predict_proba(X_test)[:, 1]
        methods["platt_sigmoid"] = {
            "roc_auc": float(roc_auc_score(y_test, y_prob_platt)),
            "pr_auc": float(average_precision_score(y_test, y_prob_platt)),
            "brier": float(brier_score_loss(y_test, y_prob_platt)),
            "ece": compute_ece(y_test.values, y_prob_platt),
            "mean_pred_prob": float(y_prob_platt.mean()),
            "calibration_curve": compute_calibration_curve(y_test.values, y_prob_platt),
            "brier_decomposition": compute_brier_decomposition(y_test.values, y_prob_platt),
        }
    except Exception as exc:
        logger.warning("Platt calibration failed: %s", exc)
        methods["platt_sigmoid"] = {"error": str(exc)}

    # 3. Isotonic calibration
    try:
        isotonic = CalibratedClassifierCV(model, method="isotonic", cv="prefit")
        isotonic.fit(X_calib, y_calib)
        y_prob_iso = isotonic.predict_proba(X_test)[:, 1]
        methods["isotonic"] = {
            "roc_auc": float(roc_auc_score(y_test, y_prob_iso)),
            "pr_auc": float(average_precision_score(y_test, y_prob_iso)),
            "brier": float(brier_score_loss(y_test, y_prob_iso)),
            "ece": compute_ece(y_test.values, y_prob_iso),
            "mean_pred_prob": float(y_prob_iso.mean()),
            "calibration_curve": compute_calibration_curve(y_test.values, y_prob_iso),
            "brier_decomposition": compute_brier_decomposition(y_test.values, y_prob_iso),
        }
    except Exception as exc:
        logger.warning("Isotonic calibration failed: %s", exc)
        methods["isotonic"] = {"error": str(exc)}

    # Recommendation
    best_method = min(
        (m for m in methods.keys() if "ece" in methods[m]),
        key=lambda m: methods[m]["ece"],
        default="uncalibrated",
    )
    methods["_recommendation"] = {
        "best_method": best_method,
        "reason": f"{best_method} has the lowest ECE ({methods[best_method]['ece']:.4f})",
    }

    return methods


def run_calibration_report(
    model_path: Path,
    X_test_path: Path,
    y_test_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    """Generate a full calibration report and save to JSON."""
    import joblib

    logger.info("Loading model from %s", model_path)
    model = joblib.load(model_path)

    logger.info("Loading test data from %s", X_test_path)
    X_test = pd.read_csv(X_test_path)
    y_test = pd.read_csv(y_test_path).iloc[:, 0]

    # Split test into calibration + evaluation (50/50)
    from sklearn.model_selection import train_test_split
    X_calib, X_eval, y_calib, y_eval = train_test_split(
        X_test, y_test, test_size=0.5, random_state=42, stratify=y_test
    )

    logger.info("Comparing calibration methods...")
    # Note: model is already fitted, so X_train/y_train are unused
    comparison = compare_calibration_methods(
        model=model,
        X_train=X_test,  # placeholder
        y_train=y_test,
        X_calib=X_calib,
        y_calib=y_calib,
        X_test=X_eval,
        y_test=y_eval,
    )

    report = {
        "report_date": _now(),
        "model_path": str(model_path),
        "test_size": len(X_test),
        "fraud_rate": float(y_test.mean()),
        "methods": comparison,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Calibration report saved to %s", output_path)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Generate model calibration report")
    parser.add_argument("--model", type=Path, default=PROJECT_ROOT / "models" / "best_fraud_model.pkl")
    parser.add_argument("--x-test", type=Path, default=PROJECT_ROOT / "data" / "processed" / "X_test.csv")
    parser.add_argument("--y-test", type=Path, default=PROJECT_ROOT / "data" / "processed" / "y_test.csv")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "calibration_report.json")
    args = parser.parse_args()

    report = run_calibration_report(args.model, args.x_test, args.y_test, args.output)
    print(f"\nRecommendation: {report['methods']['_recommendation']}")
    for method, data in report["methods"].items():
        if method == "_recommendation":
            continue
        if "error" in data:
            print(f"  {method}: FAILED ({data['error']})")
        else:
            print(f"  {method}: ECE={data['ece']:.4f}, Brier={data['brier']:.4f}, "
                  f"mean_prob={data['mean_pred_prob']:.4f}")
