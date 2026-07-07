"""
Enterprise Export Center Module.

Provides:
- Data extraction from database to Pandas
- Formatting and serialization to CSV, Excel, and JSON
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from src.db import engine

def get_export_data(
    db_path: Path,
    dataset: str,
    status_filter: str = "All",
    risk_filter: str = "All",
    limit: int = 1000,
) -> pd.DataFrame:
    """Fetch raw data for export from DB based on dataset and filters."""
    if dataset == "prediction_logs":
        query = "SELECT * FROM prediction_logs WHERE 1=1"
        params = []
        if status_filter != "All":
            query += " AND status = %s"
            params.append(status_filter)
        if risk_filter != "All":
            query += " AND final_risk_level = %s"
            params.append(risk_filter)
            
        query += f" ORDER BY id DESC LIMIT {limit}"
        
        # fallback to ? if using sqlite for tests
        if engine.dialect.name == "sqlite":
            query = query.replace("%s", "?")
            
        df = pd.read_sql_query(query, engine, params=params)
        
    elif dataset == "fraud_cases":
        query = "SELECT * FROM fraud_cases WHERE 1=1"
        params = []
        if status_filter != "All":
            query += " AND status = %s"
            params.append(status_filter)
            
        query += f" ORDER BY id DESC LIMIT {limit}"
        
        if engine.dialect.name == "sqlite":
            query = query.replace("%s", "?")
            
        df = pd.read_sql_query(query, engine, params=params)
        
    elif dataset == "audit_logs":
        df = pd.read_sql_query(f"SELECT * FROM audit_logs ORDER BY id DESC LIMIT {limit}", engine)
        
    elif dataset == "customer_profiles":
        df = pd.read_sql_query(f"SELECT * FROM customer_profiles ORDER BY risk_score_avg DESC LIMIT {limit}", engine)
        
    else:
        df = pd.DataFrame()
        
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
