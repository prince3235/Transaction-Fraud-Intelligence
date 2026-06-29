"""
Enterprise Business Rules Engine.

Provides:
- Configurable rule definitions stored in SQLite
- Priority-ordered rule evaluation
- Pre-built default rules seeded at startup
- Triggered count tracking
- Rule enable/disable toggle
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
        "condition_json": json.dumps({"field": "amount", "operator": ">", "threshold": 75000}),
        "action": "flag",
        "risk_level_bump": "HIGH",
        "priority": 90,
    },
    {
        "name": "Account Drainage",
        "description": "Sender's account fully emptied — strong fraud signal",
        "rule_type": "flag",
        "condition_json": json.dumps({"field": "sender_account_emptied", "equals": 1}),
        "action": "flag",
        "risk_level_bump": "HIGH",
        "priority": 95,
    },
    {
        "name": "High Velocity Transaction",
        "description": "Transaction occurs in a step with abnormally high activity",
        "rule_type": "flag",
        "condition_json": json.dumps({"field": "is_high_velocity_step", "equals": 1}),
        "action": "flag",
        "risk_level_bump": "MEDIUM",
        "priority": 60,
    },
    {
        "name": "New Destination Account",
        "description": "Destination account had zero balance — potential money mule",
        "rule_type": "flag",
        "condition_json": json.dumps({"field": "is_oldbalanceDest_zero", "equals": 1}),
        "action": "flag",
        "risk_level_bump": "MEDIUM",
        "priority": 70,
    },
    {
        "name": "Balance Error Detected",
        "description": "Post-transaction balance doesn't match expected — data anomaly",
        "rule_type": "threshold",
        "condition_json": json.dumps({"field": "balance_error_orig", "operator": "!=", "threshold": 0}),
        "action": "flag",
        "risk_level_bump": "MEDIUM",
        "priority": 75,
    },
    {
        "name": "High Risk Transaction Type",
        "description": "TRANSFER and CASH_OUT are highest-risk transaction types",
        "rule_type": "threshold",
        "condition_json": json.dumps({"field": "type_risk_score", "operator": ">=", "threshold": 3}),
        "action": "flag",
        "risk_level_bump": "MEDIUM",
        "priority": 65,
    },
    {
        "name": "Multiple Suspicious Signals",
        "description": "3 or more concurrent suspicious signals detected",
        "rule_type": "threshold",
        "condition_json": json.dumps({"field": "suspicious_signal_count", "operator": ">=", "threshold": 3}),
        "action": "flag",
        "risk_level_bump": "HIGH",
        "priority": 85,
    },
    {
        "name": "Critical Signal Accumulation",
        "description": "5 or more suspicious signals — automatic CRITICAL escalation",
        "rule_type": "threshold",
        "condition_json": json.dumps({"field": "suspicious_signal_count", "operator": ">=", "threshold": 5}),
        "action": "escalate",
        "risk_level_bump": "CRITICAL",
        "priority": 100,
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


# ── Database operations ───────────────────────────────────────────────────────

def seed_default_rules(db_path: Path) -> None:
    """
    Insert default rules if they don't already exist.
    Safe to call on every startup.

    Args:
        db_path: Path to SQLite database.
    """
    con = _connect(db_path)
    cur = con.cursor()
    now = _now()

    for rule in DEFAULT_RULES:
        cur.execute("SELECT id FROM business_rules WHERE name = ?", (rule["name"],))
        if cur.fetchone() is None:
            cur.execute(
                """
                INSERT INTO business_rules
                    (name, description, rule_type, condition_json, action,
                     risk_level_bump, priority, is_active, triggered_count,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
                """,
                (
                    rule["name"],
                    rule["description"],
                    rule["rule_type"],
                    rule["condition_json"],
                    rule["action"],
                    rule["risk_level_bump"],
                    rule["priority"],
                    now,
                    now,
                ),
            )

    con.commit()
    con.close()


def list_rules(db_path: Path, active_only: bool = False) -> List[Dict[str, Any]]:
    """
    List all business rules.

    Args:
        db_path: Path to SQLite database.
        active_only: If True, only return active rules.

    Returns:
        List of rule dicts, ordered by priority DESC.
    """
    query = """
        SELECT * FROM business_rules
        {}
        ORDER BY priority DESC, id ASC
    """.format("WHERE is_active = 1" if active_only else "")

    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]


def toggle_rule(db_path: Path, rule_id: int, is_active: bool) -> Optional[Dict[str, Any]]:
    """Enable or disable a business rule."""
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(
        "UPDATE business_rules SET is_active = ?, updated_at = ? WHERE id = ?",
        (1 if is_active else 0, _now(), rule_id),
    )
    con.commit()
    cur.execute("SELECT * FROM business_rules WHERE id = ?", (rule_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None


def create_rule(
    db_path: Path,
    name: str,
    description: str,
    rule_type: str,
    condition: Dict[str, Any],
    action: str,
    risk_level_bump: str,
    priority: int,
) -> Dict[str, Any]:
    """Create a new business rule."""
    now = _now()
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO business_rules
            (name, description, rule_type, condition_json, action,
             risk_level_bump, priority, is_active, triggered_count, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
        """,
        (name, description, rule_type, json.dumps(condition), action, risk_level_bump, priority, now, now),
    )
    con.commit()
    row_id = cur.lastrowid
    cur.execute("SELECT * FROM business_rules WHERE id = ?", (row_id,))
    row = cur.fetchone()
    con.close()
    return dict(row)


# ── Rule evaluation ───────────────────────────────────────────────────────────

_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _evaluate_single_rule(rule: Dict[str, Any], features: Dict[str, Any]) -> bool:
    """
    Evaluate a single rule against a feature dict.

    Supports operators: >, <, >=, <=, ==, !=
    And flag-type rules with 'equals' check.

    Args:
        rule: Rule dict from DB.
        features: Feature values from ML pipeline.

    Returns:
        True if the rule condition is satisfied.
    """
    try:
        condition = json.loads(rule["condition_json"]) if isinstance(rule["condition_json"], str) else rule["condition_json"]
    except (json.JSONDecodeError, TypeError):
        return False

    field = condition.get("field")
    if field is None or field not in features:
        return False

    value = features[field]

    # Flag-type: exact equality check
    if "equals" in condition:
        return value == condition["equals"]

    # Threshold-type: comparison
    operator = condition.get("operator", "==")
    threshold = condition.get("threshold", 0)

    try:
        v = float(value)
        t = float(threshold)
        return {
            ">": v > t,
            ">=": v >= t,
            "<": v < t,
            "<=": v <= t,
            "==": v == t,
            "!=": v != t,
        }.get(operator, False)
    except (ValueError, TypeError):
        return False


def evaluate_rules(
    db_path: Path,
    features: Dict[str, Any],
    current_risk_level: str = "LOW",
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Evaluate all active business rules against a feature set.

    Args:
        db_path: Path to SQLite database.
        features: Feature values from ML pipeline.
        current_risk_level: Starting risk level (from ML model).

    Returns:
        Tuple of (final_risk_level, list_of_triggered_rules).
    """
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
        con = _connect(db_path)
        for rule in triggered:
            con.execute(
                "UPDATE business_rules SET triggered_count = triggered_count + 1 WHERE id = ?",
                (rule["id"],),
            )
        con.commit()
        con.close()

    return final_level, triggered
