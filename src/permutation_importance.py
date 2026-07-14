"""
Permutation Importance Module.

Provides model-agnostic feature importance via permutation. Complements
SHAP (which is local per-prediction) with a global "how much does shuffling
this feature hurt model performance?" measure.

Use cases:
1. Cross-check SHAP global importance — if SHAP says feature X is #1 but
   permutation says it's irrelevant, the SHAP value may be an artifact.
2. Identify features that the model ignores (permutation importance ≈ 0)
   — candidates for removal to simplify the model.
3. Detect leakage — leaked features have abnormally high permutation
   importance because the model depends on them entirely.

Usage:
    from src.permutation_importance import compute_permutation_importance
    importance = compute_permutation_importance(model, X_test, y_test)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def compute_permutation_importance(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    metric: str = "roc_auc",
    n_repeats: int = 5,
    random_state: int = 42,
    n_jobs: int = 1,
) -> List[Dict[str, Any]]:
    """
    Compute permutation importance for each feature.

    For each feature:
    1. Record baseline metric (e.g. ROC-AUC) on (X, y)
    2. Shuffle the feature column, re-predict, re-compute metric
    3. Importance = baseline - shuffled (averaged over n_repeats)
    4. Negative importance = shuffling helped (feature may be noise)

    Args:
        model: Fitted classifier with predict_proba()
        X: Feature DataFrame
        y: True labels
        metric: 'roc_auc' or 'pr_auc'
        n_repeats: Number of shuffles per feature (default 5)
        random_state: For reproducibility
        n_jobs: Number of parallel jobs (1 = sequential)

    Returns:
        List of {feature, importance, std, baseline_metric, shuffled_metric}
        sorted by importance descending.
    """
    rng = np.random.RandomState(random_state)

    # Baseline metric
    y_prob = model.predict_proba(X)[:, 1]
    if metric == "roc_auc":
        baseline = roc_auc_score(y, y_prob)
    elif metric == "pr_auc":
        from sklearn.metrics import average_precision_score
        baseline = average_precision_score(y, y_prob)
    else:
        raise ValueError(f"Unknown metric: {metric}")

    logger.info("Baseline %s: %.4f", metric, baseline)

    results: List[Dict[str, Any]] = []
    for col in X.columns:
        importances: List[float] = []
        for _ in range(n_repeats):
            X_shuffled = X.copy()
            X_shuffled[col] = rng.permutation(X_shuffled[col].values)
            y_prob_shuffled = model.predict_proba(X_shuffled)[:, 1]
            if metric == "roc_auc":
                shuffled = roc_auc_score(y, y_prob_shuffled)
            else:
                from sklearn.metrics import average_precision_score
                shuffled = average_precision_score(y, y_prob_shuffled)
            importances.append(baseline - shuffled)

        results.append({
            "feature": col,
            "importance": float(np.mean(importances)),
            "std": float(np.std(importances)),
            "baseline_metric": float(baseline),
            "shuffled_metric_mean": float(baseline - np.mean(importances)),
        })
        logger.info("  %s: %.4f ± %.4f", col, np.mean(importances), np.std(importances))

    results.sort(key=lambda r: r["importance"], reverse=True)
    return results


def compare_with_shap(
    permutation_results: List[Dict[str, Any]],
    shap_summary_path: Path,
) -> List[Dict[str, Any]]:
    """
    Cross-check permutation importance against SHAP global importance.

    Flag features where the two methods disagree significantly — this often
    indicates either leakage or a SHAP artifact.

    Args:
        permutation_results: Output of compute_permutation_importance()
        shap_summary_path: Path to a SHAP summary JSON (feature → mean |SHAP|)

    Returns:
        List of {feature, permutation_rank, shap_rank, disagreement}
    """
    with shap_summary_path.open("r") as f:
        shap_data = json.load(f) if shap_summary_path.suffix == ".json" else None

    if shap_data is None:
        # Try reading the example alert JSON which has SHAP contributors
        import json
        with shap_summary_path.open("r") as f:
            shap_data = json.load(f)

    # Build SHAP rank lookup
    shap_importance: Dict[str, float] = {}
    if isinstance(shap_data, list):
        # List of {feature, contribution, ...}
        for item in shap_data:
            feat = item.get("feature", "")
            shap_importance[feat] = abs(item.get("contribution", item.get("shap_contribution", 0)))
    elif isinstance(shap_data, dict):
        shap_importance = {k: abs(v) for k, v in shap_data.items() if isinstance(v, (int, float))}

    shap_ranked = sorted(shap_importance.items(), key=lambda x: x[1], reverse=True)
    shap_rank = {feat: i + 1 for i, (feat, _) in enumerate(shap_ranked)}

    perm_rank = {r["feature"]: i + 1 for i, r in enumerate(permutation_results)}

    comparison: List[Dict[str, Any]] = []
    for r in permutation_results:
        feat = r["feature"]
        p_rank = perm_rank[feat]
        s_rank = shap_rank.get(feat, 999)
        disagreement = abs(p_rank - s_rank) if s_rank < 999 else 999
        comparison.append({
            "feature": feat,
            "permutation_rank": p_rank,
            "permutation_importance": r["importance"],
            "shap_rank": s_rank,
            "shap_importance": shap_importance.get(feat, 0),
            "rank_disagreement": disagreement,
            "flag": "DISAGREE" if disagreement > 5 else "OK",
        })

    return comparison


if __name__ == "__main__":
    import json
    import joblib
    from sklearn.model_selection import train_test_split

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Load model + data
    model_path = PROJECT_ROOT / "models" / "best_fraud_model.pkl"
    data_path = PROJECT_ROOT / "data" / "processed" / "X_test.csv"
    y_path = PROJECT_ROOT / "data" / "processed" / "y_test.csv"

    if not model_path.exists():
        logger.error("Model not found at %s — run dvc pull first.", model_path)
        exit(1)
    if not data_path.exists():
        logger.error("Test data not found at %s", data_path)
        exit(1)

    model = joblib.load(model_path)
    X = pd.read_csv(data_path)
    y = pd.read_csv(y_path).iloc[:, 0]

    # Sample for speed
    if len(X) > 20_000:
        X, _, y, _ = train_test_split(X, y, test_size=0.9, random_state=42, stratify=y)

    results = compute_permutation_importance(model, X, y, n_repeats=3)

    output_path = PROJECT_ROOT / "reports" / "permutation_importance.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved to %s", output_path)

    print("\nTop 10 features by permutation importance:")
    for r in results[:10]:
        print(f"  {r['feature']:40s} {r['importance']:+.4f} ± {r['std']:.4f}")
