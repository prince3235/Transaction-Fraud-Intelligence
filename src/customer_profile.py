"""
Enterprise Customer Risk Profile Module.

Provides:
- Aggregation of transaction history per customer (sender account)
- Risk profiling (average risk score, fraud count)
- Device and Location count approximations
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def get_or_create_customer_profile(db_path: Path, customer_id: str) -> Dict[str, Any]:
    """
    Fetch a customer profile. If it doesn't exist, calculate it from prediction_logs.
    """
    con = _connect(db_path)
    cur = con.cursor()
    
    cur.execute("SELECT * FROM customer_profiles WHERE customer_id = ?", (customer_id,))
    row = cur.fetchone()
    
    if row:
        con.close()
        return dict(row)
        
    # Calculate from logs if not exists (lazy generation)
    cur.execute(
        """
        SELECT 
            transaction_json, 
            final_risk_score, 
            final_risk_level,
            created_at
        FROM prediction_logs
        WHERE transaction_json LIKE ?
        ORDER BY created_at ASC
        """, 
        (f'%"{customer_id}"%',)
    )
    logs = cur.fetchall()
    
    total_tx = len(logs)
    if total_tx == 0:
        con.close()
        return {
            "customer_id": customer_id,
            "total_transactions": 0,
            "fraud_count": 0,
            "avg_amount": 0.0,
            "max_amount": 0.0,
            "risk_score_avg": 0.0,
            "risk_trend": "UNKNOWN"
        }
        
    total_amt = 0.0
    max_amt = 0.0
    fraud_count = 0
    total_risk = 0.0
    
    first_date = logs[0]["created_at"]
    last_date = logs[-1]["created_at"]
    
    for log in logs:
        try:
            tx = json.loads(log["transaction_json"])
            amt = float(tx.get("amount", 0.0))
        except:
            amt = 0.0
            
        total_amt += amt
        if amt > max_amt: max_amt = amt
        
        if log["final_risk_level"] in ("HIGH", "CRITICAL"):
            fraud_count += 1
            
        total_risk += float(log["final_risk_score"])
        
    avg_amt = total_amt / total_tx
    avg_risk = total_risk / total_tx
    
    # Simple risk trend logic based on last 5 transactions vs overall
    trend = "STABLE"
    if total_tx > 5:
        recent_logs = logs[-5:]
        recent_risk = sum(l["final_risk_score"] for l in recent_logs) / 5.0
        if recent_risk > avg_risk + 10:
            trend = "INCREASING"
        elif recent_risk < avg_risk - 10:
            trend = "DECREASING"
            
    # Insert new profile
    now = _now()
    # Device and country counts are mocked for demo based on hash of customer ID
    device_cnt = 1 + (hash(customer_id) % 3)
    country_cnt = 1 + (hash(customer_id) % 2)
    
    cur.execute(
        """
        INSERT INTO customer_profiles
            (customer_id, total_transactions, fraud_count, avg_amount, max_amount,
             risk_score_avg, last_transaction_at, first_transaction_at,
             risk_trend, device_count, country_count, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (customer_id, total_tx, fraud_count, avg_amt, max_amt, avg_risk, 
         last_date, first_date, trend, device_cnt, country_cnt, now)
    )
    con.commit()
    
    cur.execute("SELECT * FROM customer_profiles WHERE customer_id = ?", (customer_id,))
    final_row = cur.fetchone()
    con.close()
    
    return dict(final_row)


def search_customers(db_path: Path, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for customers by ID (nameOrig)."""
    con = _connect(db_path)
    cur = con.cursor()
    
    cur.execute(
        """
        SELECT * FROM customer_profiles 
        WHERE customer_id LIKE ? 
        ORDER BY risk_score_avg DESC 
        LIMIT ?
        """, 
        (f"%{query}%", limit)
    )
    rows = cur.fetchall()
    
    # If not found in profiles but might exist in logs, we can trigger a lazy generation
    if not rows and len(query) > 3:
        cur.execute(
            """
            SELECT transaction_json FROM prediction_logs 
            WHERE transaction_json LIKE ? 
            LIMIT 5
            """, 
            (f'%"nameOrig": "{query}%"',)
        )
        tx_rows = cur.fetchall()
        for r in tx_rows:
            try:
                tx = json.loads(r[0])
                cid = tx.get("nameOrig")
                if cid and cid.startswith(query):
                    # Lazy create
                    get_or_create_customer_profile(db_path, cid)
            except:
                pass
                
        # Re-query
        cur.execute(
            """
            SELECT * FROM customer_profiles 
            WHERE customer_id LIKE ? 
            ORDER BY risk_score_avg DESC 
            LIMIT ?
            """, 
            (f"%{query}%", limit)
        )
        rows = cur.fetchall()
        
    con.close()
    return [dict(r) for r in rows]
