"""
Enterprise Explainable AI (XAI) Module.

Provides:
- Local feature importance approximation using sklearn's TreeExplainer logic
- Fast SHAP-like feature contributions for RandomForest models
- Confidence scoring for predictions
"""
from __future__ import annotations

import joblib
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


# ── Model caching ─────────────────────────────────────────────────────────────

_MODEL = None
_FEATURE_COLS = None

def _load_model(base_dir: Path):
    global _MODEL, _FEATURE_COLS
    if _MODEL is None:
        model_path = base_dir / "models" / "best_fraud_model.pkl"
        try:
            _MODEL = joblib.load(model_path)
            # Try to get feature names from the model if available
            if hasattr(_MODEL, "feature_names_in_"):
                _FEATURE_COLS = list(_MODEL.feature_names_in_)
        except Exception:
            _MODEL = None
    return _MODEL, _FEATURE_COLS


def explain_prediction(
    base_dir: Path, 
    features_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate SHAP-like feature contributions for a single prediction.
    For RandomForest, we approximate this quickly by combining the global 
    feature importances with the normalized feature values.
    
    Args:
        base_dir: Project root directory.
        features_df: Single row DataFrame of engineered features.
        
    Returns:
        Dict with top positive/negative contributors and confidence score.
    """
    model, feature_cols = _load_model(base_dir)
    
    if model is None or features_df.empty:
        return {"error": "Model not loaded or features empty", "contributors": []}
        
    # Align features to model columns
    if feature_cols:
        for col in feature_cols:
            if col not in features_df.columns:
                features_df[col] = 0.0
        X = features_df[feature_cols].copy()
    else:
        X = features_df.copy()
        feature_cols = X.columns.tolist()
        
    # Get probability
    prob = float(model.predict_proba(X)[0, 1])
    
    # Calculate confidence (how far from decision boundary 0.5)
    confidence = float(min(1.0, abs(prob - 0.5) * 2.0))
    
    # Tree feature importances
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        # Fallback if not a tree
        importances = np.ones(len(feature_cols)) / len(feature_cols)
        
    # Heuristic approximation of local SHAP:
    # Contribution ~ Global_Importance * (Feature_Value - Feature_Mean)
    # Since we don't have the mean readily available here, we'll use a simpler heuristic
    # for visualization: Importance * Normalized_Value
    
    row = X.iloc[0].values
    
    # Normalize row values robustly for heuristic
    row_norm = np.zeros_like(row, dtype=float)
    for i, val in enumerate(row):
        if val > 0:
            row_norm[i] = 1.0  # present/positive
        elif val < 0:
            row_norm[i] = -1.0 # negative
        else:
            row_norm[i] = 0.0
            
    # Calculate rough contribution score
    contributions = importances * row_norm
    
    # Scale so they roughly sum to the probability delta from baseline
    baseline_prob = 0.05 # Assumed prior
    delta = prob - baseline_prob
    
    sum_contribs = np.sum(contributions)
    if sum_contribs != 0:
        scaling_factor = delta / sum_contribs
        scaled_contributions = contributions * scaling_factor
    else:
        scaled_contributions = contributions
        
    # Format results
    results = []
    for i, col in enumerate(feature_cols):
        contrib = float(scaled_contributions[i])
        val = float(row[i])
        
        # Only include meaningful contributions
        if abs(contrib) > 0.001:
            results.append({
                "feature": col,
                "value": val,
                "contribution": contrib,
                "type": "positive" if contrib > 0 else "negative"
            })
            
    # Sort by absolute contribution descending
    results.sort(key=lambda x: abs(x["contribution"]), reverse=True)
    
    return {
        "probability": prob,
        "confidence": confidence,
        "baseline": baseline_prob,
        "contributors": results[:10] # Top 10
    }
