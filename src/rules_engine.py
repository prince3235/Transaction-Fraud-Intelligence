"""
Enterprise Business Rules Engine.

Provides:
- Configurable rule definitions stored in Postgres
- Priority-ordered rule evaluation
- Pre-built default rules seeded at startup
- Triggered count tracking
- Rule enable/disable toggle
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import simpleeval
from src.db import SessionLocal
from src.models import BusinessRule


# ── Rule types ────────────────────────────────────────────────────────────────

RULE_TYPES = [
    "threshold",     # Compare feature value to threshold
    "flag",          # Check boolean flag field
    "pattern",       # Pattern-based check
    "compound",      # Multiple conditions (AND/OR)
]

RISK_BUMPS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# ── Default rules (seeded at startup) ─────────────────────────────────────────

DEFAULT_RULES = [
    {
        "name": "Large Amount Transfer",
        "description": "Flag transactions above ₹75,000 — high fraud risk",
        "rule_type": "threshold",
        "condition_json": "amount > 75000",
        "action": "flag",
        "risk_level_bump": "HIGH",
        "priority": 90,
    },
    {
        "name": "Account Drainage",
        "description": "Sender's account fully emptied — strong fraud signal",
        "rule_type": "flag",
        "condition_json": "sender_account_emptied == 1",
        "action": "flag",
        "risk_level_bump": "HIGH",
        "priority": 95,
    },
    {
        "name": "High Velocity Transaction",
        "description": "Transaction occurs in a step with abnormally high activity",
        "rule_type": "flag",
        "condition_json": "is_high_velocity_step == 1",
        "action": "flag",
        "risk_level_bump": "MEDIUM",
        "priority": 60,
    },
    {
        "name": "New Destination Account",
        "description": "Destination account had zero balance — potential money mule",
        "rule_type": "flag",
        "condition_json": "is_oldbalanceDest_zero == 1",
        "action": "flag",
        "risk_level_bump": "MEDIUM",
        "priority": 70,
    },
    {
        "name": "Balance Error Detected",
        "description": "Post-transaction balance doesn't match expected — data anomaly",
        "rule_type": "threshold",
        "condition_json": "balance_error_orig != 0",
        "action": "flag",
        "risk_level_bump": "MEDIUM",
        "priority": 75,
    },
    {
        "name": "High Risk Transaction Type",
        "description": "TRANSFER and CASH_OUT are highest-risk transaction types",
        "rule_type": "threshold",
        "condition_json": "type_risk_score >= 3",
        "action": "flag",
        "risk_level_bump": "MEDIUM",
        "priority": 65,
    },
    {
        "name": "Multiple Suspicious Signals",
        "description": "3 or more concurrent suspicious signals detected",
        "rule_type": "threshold",
        "condition_json": "suspicious_signal_count >= 3",
        "action": "flag",
        "risk_level_bump": "HIGH",
        "priority": 85,
    },
    {
        "name": "Critical Signal Accumulation",
        "description": "5 or more suspicious signals — automatic CRITICAL escalation",
        "rule_type": "threshold",
        "condition_json": "suspicious_signal_count >= 5",
        "action": "escalate",
        "risk_level_bump": "CRITICAL",
        "priority": 100,
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Database operations ───────────────────────────────────────────────────────

def seed_default_rules(db_path: Path) -> None:
    """
    Insert default rules if they don't already exist.
    Safe to call on every startup.

    Args:
        db_path: Path to SQLite database. (ignored, kept for signature compat)
    """
    db = SessionLocal()
    now = _now()
    
    try:
        for rule_data in DEFAULT_RULES:
            exists = db.query(BusinessRule).filter(BusinessRule.name == rule_data["name"]).first()
            if not exists:
                new_rule = BusinessRule(
                    name=rule_data["name"],
                    description=rule_data["description"],
                    rule_type=rule_data["rule_type"],
                    condition_json=rule_data["condition_json"],
                    action=rule_data["action"],
                    risk_level_bump=rule_data["risk_level_bump"],
                    priority=rule_data["priority"],
                    is_active=True,
                    triggered_count=0,
                    created_at=now,
                    updated_at=now
                )
                db.add(new_rule)
        db.commit()
    finally:
        db.close()


def list_rules(db_path: Path, active_only: bool = False) -> List[Dict[str, Any]]:
    """
    List all business rules.
    """
    db = SessionLocal()
    try:
        query = db.query(BusinessRule)
        if active_only:
            query = query.filter(BusinessRule.is_active == True)
        
        rules = query.order_by(BusinessRule.priority.desc(), BusinessRule.id.asc()).all()
        return [{
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "rule_type": r.rule_type,
            "condition_json": r.condition_json,
            "action": r.action,
            "risk_level_bump": r.risk_level_bump,
            "priority": r.priority,
            "is_active": r.is_active,
            "triggered_count": r.triggered_count,
            "created_at": r.created_at,
            "updated_at": r.updated_at
        } for r in rules]
    finally:
        db.close()


def toggle_rule(db_path: Path, rule_id: int, is_active: bool) -> Optional[Dict[str, Any]]:
    """Enable or disable a business rule."""
    db = SessionLocal()
    try:
        rule = db.query(BusinessRule).filter(BusinessRule.id == rule_id).first()
        if rule:
            rule.is_active = is_active
            rule.updated_at = _now()
            db.commit()
            db.refresh(rule)
            return {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "rule_type": rule.rule_type,
                "condition_json": rule.condition_json,
                "action": rule.action,
                "risk_level_bump": rule.risk_level_bump,
                "priority": rule.priority,
                "is_active": rule.is_active,
                "triggered_count": rule.triggered_count,
                "created_at": rule.created_at,
                "updated_at": rule.updated_at
            }
        return None
    finally:
        db.close()


def create_rule(
    db_path: Path,
    name: str,
    description: str,
    rule_type: str,
    condition: str,
    action: str,
    risk_level_bump: str,
    priority: int,
) -> Dict[str, Any]:
    """Create a new business rule."""
    if "__" in condition:
        raise ValueError("Invalid expression: '__' is not allowed")
    if len(condition) > 500:
        raise ValueError("Invalid expression: exceeds 500 characters")
        
    class DummyDict(dict):
        def __getitem__(self, key):
            return 0
    try:
        evaluator = simpleeval.SimpleEval(names=DummyDict(), functions={"abs": abs})
        evaluator.eval(condition)
    except (simpleeval.InvalidExpression, SyntaxError) as e:
        raise ValueError(f"Invalid rule syntax: {e}")
    except (simpleeval.NameNotDefined, simpleeval.FunctionNotDefined):
        pass
    except Exception as e:
        raise ValueError(f"Invalid rule: {e}")

    now = _now()
    db = SessionLocal()
    try:
        rule = BusinessRule(
            name=name,
            description=description,
            rule_type=rule_type,
            condition_json=condition,
            action=action,
            risk_level_bump=risk_level_bump,
            priority=priority,
            is_active=True,
            triggered_count=0,
            created_at=now,
            updated_at=now
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "rule_type": rule.rule_type,
            "condition_json": rule.condition_json,
            "action": rule.action,
            "risk_level_bump": rule.risk_level_bump,
            "priority": rule.priority,
            "is_active": rule.is_active,
            "triggered_count": rule.triggered_count,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at
        }
    finally:
        db.close()


# ── Rule evaluation ───────────────────────────────────────────────────────────

_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _evaluate_single_rule(rule: Dict[str, Any], features: Dict[str, Any]) -> bool:
    """
    Evaluate a single rule against a feature dict.

    Uses simpleeval for safe mathematical/logical expression evaluation.

    Args:
        rule: Rule dict from DB.
        features: Feature values from ML pipeline.

    Returns:
        True if the rule condition is satisfied.
    """
    condition = rule.get("condition_json", "")
    if not isinstance(condition, str):
        # Graceful fail if legacy JSON wasn't migrated
        print(f"Warning: Rule '{rule['name']}' condition is not a string expression. Run migration.")
        return False

    try:
        evaluator = simpleeval.SimpleEval(names=features, functions={"abs": abs})
        result = evaluator.eval(condition)
        return bool(result)
    except (simpleeval.InvalidExpression, simpleeval.NameNotDefined, simpleeval.FunctionNotDefined, SyntaxError) as e:
        print(f"Warning: Rule '{rule['name']}' failed to evaluate (fail-closed). Error: {e}")
        return False
    except Exception as e:
        print(f"Warning: Rule '{rule['name']}' failed unexpectedly (fail-closed). Error: {e}")
        return False


def evaluate_rules(
    db_path: Path,
    features: Dict[str, Any],
    current_risk_level: str = "LOW",
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Evaluate all active business rules against a feature set.
    """
    eval("1 + 1") # INTENTIONAL VULNERABILITY FOR TESTING GUARDRAILS
    rules = list_rules(db_path, active_only=True)
    triggered: List[Dict[str, Any]] = []
    final_level = current_risk_level

    for rule in rules:
        if _evaluate_single_rule(rule, features):
            triggered.append(rule)
            bump = rule.get("risk_level_bump", "MEDIUM")
            if _LEVEL_ORDER.get(bump, 0) > _LEVEL_ORDER.get(final_level, 0):
                final_level = bump

    if triggered:
        db = SessionLocal()
        try:
            for rule in triggered:
                db_rule = db.query(BusinessRule).filter(BusinessRule.id == rule["id"]).first()
                if db_rule:
                    db_rule.triggered_count += 1
            db.commit()
        finally:
            db.close()

    return final_level, triggered
