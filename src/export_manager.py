"""
Enterprise Export Center Module.

Provides:
- Data extraction from SQLite to Pandas
- Formatting and serialization to CSV, Excel, and JSON
"""
from __future__ import annotations

import io
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def get_export_data(
    db_path: Path,
    dataset: str,
    status_filter: str = "All",
    risk_filter: str = "All",
    limit: int = 1000,
) -> pd.DataFrame:
    """Fetch raw data for export from SQLite based on dataset and filters."""
    con = _connect(db_path)
    
    if dataset == "prediction_logs":
        query = "SELECT * FROM prediction_logs WHERE 1=1"
        params = []
        if status_filter != "All":
            query += " AND status = ?"
            params.append(status_filter)
        if risk_filter != "All":
            query += " AND final_risk_level = ?"
            params.append(risk_filter)
            
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, con, params=params)
        
    elif dataset == "fraud_cases":
        query = "SELECT * FROM fraud_cases WHERE 1=1"
        params = []
        if status_filter != "All":
            query += " AND status = ?"
            params.append(status_filter)
            
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, con, params=params)
        
    elif dataset == "audit_logs":
        df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", con, params=[limit])
        
    elif dataset == "customer_profiles":
        df = pd.read_sql_query("SELECT * FROM customer_profiles ORDER BY risk_score_avg DESC LIMIT ?", con, params=[limit])
        
    else:
        df = pd.DataFrame()
        
    con.close()
    return df


def to_csv(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes."""
    if df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")


def to_excel(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel (.xlsx) bytes using openpyxl."""
    if df.empty:
        return b""
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Export Data')
    return output.getvalue()


def to_json(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to JSON bytes."""
    if df.empty:
        return b"[]"
    return df.to_json(orient="records", indent=2).encode("utf-8")
