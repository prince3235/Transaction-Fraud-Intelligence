"""
Enterprise Authentication & Role-Based Access Control.

Provides:
- Password hashing with hashlib (no external deps)
- Simple token-based session management
- Role permissions matrix
- Demo user seeding
- Audit logging of login events
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Role definitions ──────────────────────────────────────────────────────────

ROLES = {
    "Admin": {
        "label": "Admin",
        "color": "#FF2D55",
        "icon": "🔴",
        "permissions": [
            "view_dashboard", "view_alerts", "view_cases",
            "manage_cases", "manage_rules", "view_model",
            "retrain_model", "view_audit", "export_data",
            "manage_users", "view_executive",
        ],
    },
    "Fraud_Analyst": {
        "label": "Fraud Analyst",
        "color": "#FF8A00",
        "icon": "🟠",
        "permissions": [
            "view_dashboard", "view_alerts", "view_cases",
            "manage_cases", "view_model", "export_data",
        ],
    },
    "Compliance_Officer": {
        "label": "Compliance Officer",
        "color": "#A855F7",
        "icon": "🟣",
        "permissions": [
            "view_dashboard", "view_alerts", "view_cases",
            "manage_cases", "manage_rules", "view_audit",
            "export_data", "view_executive",
        ],
    },
    "Auditor": {
        "label": "Auditor",
        "color": "#00B4FF",
        "icon": "🔵",
        "permissions": [
            "view_dashboard", "view_alerts", "view_cases",
            "view_audit", "view_model", "export_data",
        ],
    },
    "Viewer": {
        "label": "Viewer",
        "color": "#8899AA",
        "icon": "⚪",
        "permissions": [
            "view_dashboard", "view_alerts",
        ],
    },
}

# ── Demo users (username → {password, role}) ──────────────────────────────────

DEMO_USERS = [
    {"username": "admin",      "password": "admin123",    "role": "Admin",               "email": "admin@fraudiq.ai"},
    {"username": "analyst",    "password": "analyst123",  "role": "Fraud_Analyst",        "email": "analyst@fraudiq.ai"},
    {"username": "compliance", "password": "comply123",   "role": "Compliance_Officer",   "email": "compliance@fraudiq.ai"},
    {"username": "auditor",    "password": "audit123",    "role": "Auditor",              "email": "auditor@fraudiq.ai"},
    {"username": "viewer",     "password": "view123",     "role": "Viewer",               "email": "viewer@fraudiq.ai"},
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256 with a salt prefix.
    No external libraries required.
    """
    salt = "fraudiq_enterprise_2024"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against its stored hash."""
    return hash_password(password) == hashed


def generate_session_token() -> str:
    """Generate a cryptographically secure random session token."""
    return secrets.token_hex(32)


# ── User management ───────────────────────────────────────────────────────────

def seed_demo_users(db_path: Path) -> None:
    """
    Seed the database with demo users if they don't already exist.
    Safe to call multiple times — only inserts missing users.

    Args:
        db_path: Path to SQLite database.
    """
    con = _connect(db_path)
    cur = con.cursor()

    for user in DEMO_USERS:
        cur.execute("SELECT id FROM users WHERE username = ?", (user["username"],))
        if cur.fetchone() is None:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    user["username"],
                    user["email"],
                    hash_password(user["password"]),
                    user["role"],
                    _now(),
                ),
            )

    con.commit()
    con.close()


def authenticate(db_path: Path, username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user by username and password.

    Args:
        db_path: Path to SQLite database.
        username: Username to authenticate.
        password: Plaintext password.

    Returns:
        User dict if authentication succeeds, None otherwise.
    """
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM users WHERE username = ? AND is_active = 1",
        (username,),
    )
    row = cur.fetchone()
    con.close()

    if not row:
        return None

    user = dict(row)
    if not verify_password(password, user["password_hash"]):
        return None

    # Update last_login
    con = _connect(db_path)
    con.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (_now(), user["id"]),
    )
    con.commit()
    con.close()

    # Don't return the password hash
    user.pop("password_hash", None)
    return user


def get_user_by_username(db_path: Path, username: str) -> Optional[Dict[str, Any]]:
    """Fetch a user by username (without password hash)."""
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    user = dict(row)
    user.pop("password_hash", None)
    return user


def list_users(db_path: Path) -> List[Dict[str, Any]]:
    """Return all users (without password hashes)."""
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT id, username, email, role, is_active, created_at, last_login FROM users ORDER BY id")
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]


# ── Permission checking ───────────────────────────────────────────────────────

def has_permission(role: str, permission: str) -> bool:
    """
    Check if a given role has a specific permission.

    Args:
        role: User role name.
        permission: Permission string to check.

    Returns:
        True if the role has the permission.
    """
    role_def = ROLES.get(role, {})
    return permission in role_def.get("permissions", [])


def get_role_info(role: str) -> Dict[str, Any]:
    """Return role metadata (label, color, icon, permissions)."""
    return ROLES.get(role, ROLES["Viewer"])


# ── Audit logging ─────────────────────────────────────────────────────────────

def log_audit_event(
    db_path: Path,
    username: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    ip_address: str = "127.0.0.1",
    reason: Optional[str] = None,
) -> None:
    """
    Write an enterprise audit log entry.

    Args:
        db_path: Path to SQLite database.
        username: Actor's username.
        action: Human-readable action description (e.g., "Case Status Updated").
        entity_type: Type of entity affected (e.g., "fraud_case", "rule").
        entity_id: ID or identifier of the affected entity.
        old_value: Previous value (will be JSON-serialized).
        new_value: New value (will be JSON-serialized).
        ip_address: Actor's IP address.
        reason: Optional reason for the action.
    """
    con = _connect(db_path)
    con.execute(
        """
        INSERT INTO audit_logs
            (username, action, entity_type, entity_id,
             old_value_json, new_value_json, ip_address, reason, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            action,
            entity_type,
            str(entity_id) if entity_id is not None else None,
            json.dumps(old_value) if old_value is not None else None,
            json.dumps(new_value) if new_value is not None else None,
            ip_address,
            reason,
            _now(),
        ),
    )
    con.commit()
    con.close()


def fetch_audit_logs(
    db_path: Path,
    username: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Fetch audit log entries with optional filters."""
    clauses: List[str] = []
    params: List[Any] = []

    if username:
        clauses.append("username = ?")
        params.append(username)
    if entity_type:
        clauses.append("entity_type = ?")
        params.append(entity_type)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM audit_logs {where} ORDER BY id DESC LIMIT ?"
    params.append(limit)

    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    con.close()
    return [dict(r) for r in rows]
