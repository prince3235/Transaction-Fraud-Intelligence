"""
Enterprise Customer Risk Profile Module.

Provides:
- Aggregation of transaction history per customer (sender account)
- Risk profiling (average risk score, fraud count)
- Device and Location count approximations (deterministic hash, NOT Python hash)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.db import SessionLocal
from src.models import CustomerProfile, PredictionLog


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_or_create_customer_profile(db_path: Path, customer_id: str) -> Dict[str, Any]:
    """
    Fetch a customer profile. If it doesn't exist, calculate it from prediction_logs.
    """
    db = SessionLocal()
    try:
        profile = db.query(CustomerProfile).filter(CustomerProfile.customer_id == customer_id).first()
        
        if profile:
            return {
                "id": profile.id,
                "customer_id": profile.customer_id,
                "total_transactions": profile.total_transactions,
                "fraud_count": profile.fraud_count,
                "avg_amount": profile.avg_amount,
                "max_amount": profile.max_amount,
                "risk_score_avg": profile.risk_score_avg,
                "last_transaction_at": profile.last_transaction_at,
                "first_transaction_at": profile.first_transaction_at,
                "risk_trend": profile.risk_trend,
                "device_count": profile.device_count,
                "country_count": profile.country_count,
                "updated_at": profile.updated_at
            }
            
        # Calculate from logs if not exists (lazy generation)
        logs = db.query(PredictionLog).filter(PredictionLog.transaction_json.op('->>')('nameOrig') == customer_id).order_by(PredictionLog.created_at.asc()).all()
        # Fallback if dialect doesn't support JSON ops:
        if not logs:
            # PostgreSQL casting for JSONB to TEXT:
            from sqlalchemy import cast, String
            logs = db.query(PredictionLog).filter(cast(PredictionLog.transaction_json, String).like(f'%"{customer_id}"%')).order_by(PredictionLog.created_at.asc()).all()
            
        total_tx = len(logs)
        if total_tx == 0:
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
        
        first_date = logs[0].created_at
        last_date = logs[-1].created_at
        
        for log in logs:
            try:
                tx = log.transaction_json or {}
                amt = float(tx.get("amount", 0.0))
            except:
                amt = 0.0
                
            total_amt += amt
            if amt > max_amt: max_amt = amt
            
            if log.final_risk_level in ("HIGH", "CRITICAL"):
                fraud_count += 1
                
            total_risk += float(log.final_risk_score)
            
        avg_amt = total_amt / total_tx
        avg_risk = total_risk / total_tx
        
        # Simple risk trend logic based on last 5 transactions vs overall
        trend = "STABLE"
        if total_tx > 5:
            recent_logs = logs[-5:]
            recent_risk = sum(l.final_risk_score for l in recent_logs) / 5.0
            if recent_risk > avg_risk + 10:
                trend = "INCREASING"
            elif recent_risk < avg_risk - 10:
                trend = "DECREASING"
                
        # Insert new profile
        now = _now()
        # Device and country counts are mocked for demo, but we use a
        # DETERMINISTIC hash (sha256) instead of Python's builtin hash().
        # Python's hash() is salted per-process (PYTHONHASHSEED), so the same
        # customer got different counts on each restart — corrupting persisted
        # profiles. sha256 is deterministic across processes and machines.
        cust_hash = int(hashlib.sha256(customer_id.encode("utf-8")).hexdigest(), 16)
        device_cnt = 1 + (cust_hash % 3)
        country_cnt = 1 + (cust_hash % 2)
        
        new_profile = CustomerProfile(
            customer_id=customer_id,
            total_transactions=total_tx,
            fraud_count=fraud_count,
            avg_amount=avg_amt,
            max_amount=max_amt,
            risk_score_avg=avg_risk,
            last_transaction_at=last_date,
            first_transaction_at=first_date,
            risk_trend=trend,
            device_count=device_cnt,
            country_count=country_cnt,
            updated_at=now
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        
        return {
            "id": new_profile.id,
            "customer_id": new_profile.customer_id,
            "total_transactions": new_profile.total_transactions,
            "fraud_count": new_profile.fraud_count,
            "avg_amount": new_profile.avg_amount,
            "max_amount": new_profile.max_amount,
            "risk_score_avg": new_profile.risk_score_avg,
            "last_transaction_at": new_profile.last_transaction_at,
            "first_transaction_at": new_profile.first_transaction_at,
            "risk_trend": new_profile.risk_trend,
            "device_count": new_profile.device_count,
            "country_count": new_profile.country_count,
            "updated_at": new_profile.updated_at
        }
    finally:
        db.close()


def search_customers(db_path: Path, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for customers by ID (nameOrig)."""
    db = SessionLocal()
    try:
        profiles = db.query(CustomerProfile).filter(CustomerProfile.customer_id.like(f"%{query}%")).order_by(CustomerProfile.risk_score_avg.desc()).limit(limit).all()
        
        # If not found in profiles but might exist in logs, we can trigger a lazy generation
        if not profiles and len(query) > 3:
            from sqlalchemy import cast, String
            tx_logs = db.query(PredictionLog).filter(cast(PredictionLog.transaction_json, String).like(f'%"nameOrig": "{query}%"')).limit(5).all()
            for log in tx_logs:
                try:
                    tx = log.transaction_json or {}
                    cid = tx.get("nameOrig")
                    if cid and cid.startswith(query):
                        # Lazy create
                        get_or_create_customer_profile(db_path, cid)
                except:
                    pass
                    
            # Re-query
            profiles = db.query(CustomerProfile).filter(CustomerProfile.customer_id.like(f"%{query}%")).order_by(CustomerProfile.risk_score_avg.desc()).limit(limit).all()
            
        return [{
            "id": p.id,
            "customer_id": p.customer_id,
            "total_transactions": p.total_transactions,
            "fraud_count": p.fraud_count,
            "avg_amount": p.avg_amount,
            "max_amount": p.max_amount,
            "risk_score_avg": p.risk_score_avg,
            "last_transaction_at": p.last_transaction_at,
            "first_transaction_at": p.first_transaction_at,
            "risk_trend": p.risk_trend,
            "device_count": p.device_count,
            "country_count": p.country_count,
            "updated_at": p.updated_at
        } for p in profiles]
    finally:
        db.close()
