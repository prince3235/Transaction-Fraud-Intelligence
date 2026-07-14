"""
Enterprise Explainable AI (XAI) Module.

Previously this module computed a "SHAP-like" heuristic:
    contribution = global_importance × sign(feature_value)
This discarded feature magnitude entirely and produced attributions that did
NOT match the real SHAP values from the training notebooks.

This rewrite uses `shap.TreeExplainer` (the exact algorithm used in
notebook 07_explainability_shap.ipynb) so that serving-time explanations
match training-time explanations. The explainer is cached on first use for
performance — TreeExplainer is O(TLD) per tree which is fast for 200 trees.
"""
from __future__ import annotations

import logging
import joblib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Model + explainer cache ──────────────────────────────────────────────────

_MODEL = None
_EXPLAINER = None
_FEATURE_COLS: Optional[List[str]] = None


def _load_model_and_explainer(base_dir: Path):
    """Load the model (cached) and build a TreeExplainer (cached).

    Returns (model, explainer, feature_cols). If shap is not installed or the
    model isn't a tree ensemble, falls back to a global-importance approximation
    (clearly labeled as such in the response).
    """
    global _MODEL, _EXPLAINER, _FEATURE_COLS

    if _MODEL is None:
        model_path = base_dir / "models" / "best_fraud_model.pkl"
        try:
            _MODEL = joblib.load(model_path)
            if hasattr(_MODEL, "feature_names_in_"):
                _FEATURE_COLS = list(_MODEL.feature_names_in_)
            logger.info("XAI: model loaded from %s", model_path)
        except Exception as exc:
            logger.error("XAI: failed to load model: %s", exc)
            _MODEL = None
            return None, None, None

    if _EXPLAINER is None and _MODEL is not None:
        try:
            import shap
            # TreeExplainer works for RandomForest, XGBoost, LightGBM, etc.
            # path_dependent uses the training data's tree paths as background.
            _EXPLAINER = shap.TreeExplainer(_MODEL)
            logger.info("XAI: shap.TreeExplainer initialized (algorithm=path_dependent)")
        except ImportError:
            logger.warning(
                "XAI: shap not installed — falling back to global-importance "
                "approximation. Install with: pip install shap"
            )
            _EXPLAINER = None
        except Exception as exc:
            logger.warning("XAI: TreeExplainer init failed (%s) — using fallback.", exc)
            _EXPLAINER = None

    return _MODEL, _EXPLAINER, _FEATURE_COLS


def explain_prediction(
    base_dir: Path,
    features_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Compute real SHAP feature contributions for a single prediction.

    Uses shap.TreeExplainer (same algorithm as the training notebooks) so the
    attributions are theoretically grounded and match the offline SHAP analysis.

    Args:
        base_dir: Project root directory.
        features_df: Single-row DataFrame of engineered features.

    Returns:
        Dict with:
        - probability: model's P(fraud)
        - confidence: distance from 0.5 decision boundary
        - baseline: TreeExplainer's expected value (model's training-set base rate)
        - contributors: top-10 features by |SHAP|, with value + contribution + direction
        - method: "tree_shap" (real) or "global_importance_fallback"
    """
    model, explainer, feature_cols = _load_model_and_explainer(base_dir)

    if model is None or features_df.empty:
        return {"error": "Model not loaded or features empty", "contributors": [], "method": "none"}

    # Align features to model columns
    if feature_cols:
        for col in feature_cols:
            if col not in features_df.columns:
                features_df[col] = 0.0
        X = features_df[feature_cols].copy()
    else:
        X = features_df.copy()
        feature_cols = X.columns.tolist()

    # Model probability
    prob = float(model.predict_proba(X)[0, 1])
    confidence = float(min(1.0, abs(prob - 0.5) * 2.0))

    # ── Real SHAP path ──────────────────────────────────────────────────────
    if explainer is not None:
        try:
            shap_values = explainer.shap_values(X, check_additivity=False)

            # For binary classifiers, shap may return:
            #   - shape (1, n_features, 2)  → pick class 1 (fraud)
            #   - shape (1, n_features)     → already class 1 (newer shap versions)
            if isinstance(shap_values, list):
                # Older shap: list of arrays per class
                sv = shap_values[1][0]  # class 1 (fraud)
            elif shap_values.ndim == 3:
                sv = shap_values[0, :, 1] if shap_values.shape[2] == 2 else shap_values[0, :, 0]
            else:
                sv = shap_values[0]

            baseline = float(explainer.expected_value)
            if isinstance(baseline, (np.ndarray, list)):
                # For binary, expected_value may be [class0_base, class1_base]
                baseline = float(baseline[1] if len(baseline) > 1 else baseline[0])

            contributions = np.asarray(sv, dtype=float)
            method = "tree_shap"
        except Exception as exc:
            logger.warning("XAI: shap computation failed (%s) — falling back.", exc)
            contributions, baseline, method = _global_importance_fallback(model, X, prob, feature_cols)
    else:
        contributions, baseline, method = _global_importance_fallback(model, X, prob, feature_cols)

    # ── Format results ──────────────────────────────────────────────────────
    row = X.iloc[0].values
    results: List[Dict[str, Any]] = []

    for i, col in enumerate(feature_cols):
        contrib = float(contributions[i]) if i < len(contributions) else 0.0
        val = float(row[i])

        if abs(contrib) > 0.0001:  # filter out negligible contributions
            results.append({
                "feature": col,
                "value": val,
                "contribution": contrib,
                "direction": "positive" if contrib > 0 else "negative",
            })

    # Sort by absolute contribution descending
    results.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    return {
        "probability": prob,
        "confidence": confidence,
        "baseline": baseline,
        "method": method,
        "contributors": results[:10],  # Top 10
    }


def get_global_feature_importance(base_dir: Path) -> Dict[str, Any]:
    """
    Return global feature importance from the cached permutation importance
    report (if available), falling back to model.feature_importances_.

    Used by the LLM Copilot to provide context like "the top 3 features driving
    fraud predictions globally are X, Y, Z".
    """
    # Try permutation importance report first (more reliable than tree importances)
    perm_path = base_dir / "reports" / "permutation_importance.json"
    if perm_path.exists():
        try:
            import json
            with perm_path.open("r") as f:
                perm_data = json.load(f)
            if perm_data:
                return {
                    "method": "permutation",
                    "top_features": [
                        {"feature": r["feature"], "importance": r["importance"]}
                        for r in perm_data[:10]
                    ],
                }
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback to model.feature_importances_ (Gini importance — biased toward
    # high-cardinality features, but always available)
    model, _, feature_cols = _load_model_and_explainer(base_dir)
    if model is not None and hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        cols = feature_cols or [f"f{i}" for i in range(len(importances))]
        pairs = sorted(zip(cols, importances), key=lambda x: x[1], reverse=True)
        return {
            "method": "gini",
            "top_features": [
                {"feature": f, "importance": float(i)} for f, i in pairs[:10]
            ],
        }

    return {"method": "none", "top_features": []}


def _global_importance_fallback(
    model, X: pd.DataFrame, prob: float, feature_cols: List[str]
) -> Tuple[np.ndarray, float, str]:
    """Fallback when shap is unavailable: use global feature importances scaled
    by the probability delta from a 5% assumed prior. Clearly labeled in the
    response as `method: "global_importance_fallback"` so consumers know these
    are NOT real SHAP values.
    """
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        importances = np.ones(len(feature_cols)) / len(feature_cols)

    # Use sign of the feature value as a rough directional hint
    row = X.iloc[0].values
    row_sign = np.sign(row)
    contributions = importances * row_sign

    # Scale to sum to (prob - 0.05) — the assumed-prior delta
    baseline = 0.05
    delta = prob - baseline
    sum_c = float(np.sum(contributions))
    if abs(sum_c) > 1e-9:
        contributions = contributions * (delta / sum_c)

    return contributions, baseline, "global_importance_fallback"
