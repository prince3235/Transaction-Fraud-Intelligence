from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


TYPE_ENCODING = {"CASH_IN": 0, "CASH_OUT": 1, "DEBIT": 2, "PAYMENT": 3, "TRANSFER": 4}
TYPE_RISK = {"CASH_OUT": 3, "TRANSFER": 3, "DEBIT": 2, "CASH_IN": 1, "PAYMENT": 1}


def _safe_div(a: float, b: float) -> float:
    return float(a / b) if b and b > 0 else 0.0


def load_json(path: Path) -> Any:
    with path.open("r") as f:
        return json.load(f)


def build_features(tx: Dict[str, Any], config: Dict[str, Any]) -> pd.DataFrame:
    """
    Required keys in tx:
    step, type, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest
    """
    step = int(tx["step"])
    ttype = str(tx["type"]).upper()
    amount = float(tx["amount"])
    oldbalanceOrg = float(tx["oldbalanceOrg"])
    newbalanceOrig = float(tx["newbalanceOrig"])
    oldbalanceDest = float(tx["oldbalanceDest"])
    newbalanceDest = float(tx["newbalanceDest"])

    type_encoded = TYPE_ENCODING.get(ttype, -1)
    type_risk_score = TYPE_RISK.get(ttype, 0)

    is_oldbalanceOrg_zero = int(oldbalanceOrg == 0)
    is_newbalanceOrig_zero = int(newbalanceOrig == 0)
    is_oldbalanceDest_zero = int(oldbalanceDest == 0)
    is_newbalanceDest_zero = int(newbalanceDest == 0)

    log_amount = float(np.log1p(amount))

    balance_change_orig = newbalanceOrig - oldbalanceOrg
    expected_balance_change_orig = oldbalanceOrg - amount
    balance_error_orig = newbalanceOrig - expected_balance_change_orig

    balance_change_dest = newbalanceDest - oldbalanceDest
    expected_balance_change_dest = oldbalanceDest + amount
    balance_error_dest = newbalanceDest - expected_balance_change_dest

    amount_to_oldbalance_orig_ratio = _safe_div(amount, oldbalanceOrg)
    amount_to_oldbalance_dest_ratio = _safe_div(amount, oldbalanceDest)

    sender_account_emptied = int((oldbalanceOrg > 0) and (newbalanceOrig == 0))
    dest_received_large_amount = int((oldbalanceDest == 0) and (newbalanceDest > 0))

    large_threshold = float(config["large_threshold_p95"])
    is_large_transaction = int(amount > large_threshold)

    step_bins = config["step_bins"]
    step_bucket = int(pd.cut([step], bins=step_bins, labels=False, include_lowest=True)[0])

    step_counts = config["step_counts"]
    transactions_in_step = int(step_counts.get(str(step), 0))
    median_tx_in_step = float(config["median_transactions_in_step"])
    is_high_velocity_step = int(transactions_in_step > median_tx_in_step)

    median_oldbalanceDest = float(config["median_oldbalanceDest"])
    is_dest_high_balance = int(oldbalanceDest > median_oldbalanceDest)

    suspicious_signal_count = int(
        sender_account_emptied
        + is_large_transaction
        + dest_received_large_amount
        + int(abs(balance_error_orig) > 0)
        + int(abs(balance_error_dest) > 0)
        + int(amount_to_oldbalance_orig_ratio > 1)
    )

    row = {
        "step": step,
        "amount": amount,
        "oldbalanceOrg": oldbalanceOrg,
        "newbalanceOrig": newbalanceOrig,
        "oldbalanceDest": oldbalanceDest,
        "newbalanceDest": newbalanceDest,
        "type_encoded": type_encoded,
        "type_risk_score": type_risk_score,
        "is_oldbalanceOrg_zero": is_oldbalanceOrg_zero,
        "is_newbalanceOrig_zero": is_newbalanceOrig_zero,
        "is_oldbalanceDest_zero": is_oldbalanceDest_zero,
        "is_newbalanceDest_zero": is_newbalanceDest_zero,
        "log_amount": log_amount,
        "balance_change_orig": balance_change_orig,
        "expected_balance_change_orig": expected_balance_change_orig,
        "balance_error_orig": balance_error_orig,
        "balance_change_dest": balance_change_dest,
        "expected_balance_change_dest": expected_balance_change_dest,
        "balance_error_dest": balance_error_dest,
        "amount_to_oldbalance_orig_ratio": amount_to_oldbalance_orig_ratio,
        "amount_to_oldbalance_dest_ratio": amount_to_oldbalance_dest_ratio,
        "sender_account_emptied": sender_account_emptied,
        "dest_received_large_amount": dest_received_large_amount,
        "is_large_transaction": is_large_transaction,
        "step_bucket": step_bucket,
        "transactions_in_step": transactions_in_step,
        "is_high_velocity_step": is_high_velocity_step,
        "is_dest_high_balance": is_dest_high_balance,
        "suspicious_signal_count": suspicious_signal_count,
    }

    return pd.DataFrame([row])


def align_to_model_columns(X: pd.DataFrame, model_columns: List[str]) -> pd.DataFrame:
    """
    Ensures same columns + same order as training.
    Missing columns => filled with 0.
    Extra columns => dropped.
    """
    X_aligned = X.copy()
    for col in model_columns:
        if col not in X_aligned.columns:
            X_aligned[col] = 0

    X_aligned = X_aligned[model_columns]
    return X_aligned

def load_feature_config() -> dict:
    from pathlib import Path
    config_path = Path(__file__).resolve().parent.parent / "models" / "feature_config.json"
    return load_json(config_path) 