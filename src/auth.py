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
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.db import SessionLocal
from src.models import User, AuditLog

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
    """
    db = SessionLocal()
    try:
        now = _now()
        for user_data in DEMO_USERS:
            exists = db.query(User).filter(User.username == user_data["username"]).first()
            if not exists:
                new_user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=hash_password(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                    created_at=now
                )
                db.add(new_user)
        db.commit()
    finally:
        db.close()


def authenticate(db_path: Path, username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user by username and password.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.is_active == True).first()
        if not user or not verify_password(password, user.password_hash):
            return None
            
        user.last_login = _now()
        db.commit()
        db.refresh(user)
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        }
    finally:
        db.close()


def get_user_by_username(db_path: Path, username: str) -> Optional[Dict[str, Any]]:
    """Fetch a user by username (without password hash)."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        }
    finally:
        db.close()


def list_users(db_path: Path) -> List[Dict[str, Any]]:
    """Return all users (without password hashes)."""
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id).all()
        return [{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "last_login": u.last_login
        } for u in users]
    finally:
        db.close()


# ── Permission checking ───────────────────────────────────────────────────────

def has_permission(role: str, permission: str) -> bool:
    """Check if a given role has a specific permission."""
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
    """Write an enterprise audit log entry."""
    db = SessionLocal()
    try:
        log = AuditLog(
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_value_json=old_value,
            new_value_json=new_value,
            ip_address=ip_address,
            reason=reason,
            timestamp=_now()
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


def fetch_audit_logs(
    db_path: Path,
    username: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Fetch audit log entries with optional filters."""
    db = SessionLocal()
    try:
        query = db.query(AuditLog)
        if username:
            query = query.filter(AuditLog.username == username)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
            
        logs = query.order_by(AuditLog.id.desc()).limit(limit).all()
        return [{
            "id": log.id,
            "username": log.username,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_value_json": log.old_value_json,
            "new_value_json": log.new_value_json,
            "ip_address": log.ip_address,
            "reason": log.reason,
            "timestamp": log.timestamp
        } for log in logs]
    finally:
        db.close()
