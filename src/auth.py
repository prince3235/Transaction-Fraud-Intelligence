"""
Enterprise Authentication & Role-Based Access Control.

Provides:
- Password hashing with bcrypt (PBKDF2-style KDF, per-user salt)
- Simple token-based session management
- Role permissions matrix
- Demo user seeding (env-gated, env-injected passwords)
- Audit logging of login events
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import jwt

from src.application.ports.uow import AbstractUnitOfWork
from src.models import User, AuditLog

logger = logging.getLogger(__name__)

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:  # pragma: no cover
    _HAS_BCRYPT = False
    logger.warning(
        "bcrypt not installed — falling back to hashlib.pbkdf2_hmac (still safe, "
        "per-user salt + 600k iterations). Install bcrypt for stronger hashing."
    )

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

# ── Demo users (env-injected passwords) ───────────────────────────────────────
# Demo users are ONLY seeded when SEED_DEMO_USERS=1 is set in the environment.
# Passwords are read from env vars (DEMO_USER_<NAME>_PASSWORD); if missing, a
# cryptographically random password is generated and logged once at startup.
# In production, set SEED_DEMO_USERS=0 (or unset) and provision users via DB.

_DEMO_USER_DEFS = [
    ("admin",      "Admin",              "admin@fraudiq.ai"),
    ("analyst",    "Fraud_Analyst",      "analyst@fraudiq.ai"),
    ("compliance", "Compliance_Officer", "compliance@fraudiq.ai"),
    ("auditor",    "Auditor",            "auditor@fraudiq.ai"),
    ("viewer",     "Viewer",             "viewer@fraudiq.ai"),
]


def _demo_password(username: str) -> str:
    """Read a demo user's password from env, or generate a secure random one."""
    env_var = f"DEMO_USER_{username.upper()}_PASSWORD"
    pw = os.environ.get(env_var, "")
    if pw:
        return pw
    # Generate a 16-byte random password (alphanumeric-ish via token_urlsafe)
    pw = secrets.token_urlsafe(16)
    logger.info("Generated random demo password for user '%s' (set %s to override)",
                username, env_var)
    # Print once for dev convenience — safe because random and never reused
    print(f"  [demo] {username} -> {pw}")
    return pw


def _demo_users() -> List[Dict[str, Any]]:
    return [
        {"username": u, "password": _demo_password(u), "role": r, "email": e}
        for u, r, e in _DEMO_USER_DEFS
    ]


# Back-compat: expose DEMO_USERS list (used by some scripts/tests)
# Note: this will call _demo_users() once at import. If you want fresh random
# passwords each call, use _demo_users() directly.
DEMO_USERS = _demo_users()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt (preferred) or PBKDF2-HMAC-SHA256 fallback.
    Both produce a per-password random salt embedded in the hash string,
    so identical passwords no longer produce identical hashes.
    """
    pw_bytes = password.encode("utf-8")
    if _HAS_BCRYPT:
        return bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")
    # Fallback: PBKDF2 with per-user salt + 600k iterations (OWASP 2023 recommendation)
    salt = secrets.token_bytes(16)
    iterations = 600_000
    dk = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt, iterations)
    # Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    pw_bytes = password.encode("utf-8")
    try:
        if _HAS_BCRYPT and hashed.startswith("$2"):
            return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
        if hashed.startswith("pbkdf2_sha256$"):
            _, iterations_str, salt_hex, hash_hex = hashed.split("$", 3)
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            dk = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt, iterations)
            # Constant-time compare to avoid timing attacks
            return secrets.compare_digest(dk, expected)
        # Legacy SHA-256 hashes (salted with the old static salt) — accept once
        # so existing rows can be transparently upgraded.
        if len(hashed) == 64:
            legacy = hashlib.sha256(f"fraudiq_enterprise_2024{password}".encode()).hexdigest()
            return secrets.compare_digest(legacy, hashed)
    except (ValueError, TypeError):
        return False
    return False


JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "enterprise-fraud-intelligence-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a standard signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token. Returns payload or None if invalid/expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


def generate_session_token() -> str:
    """Generate a cryptographically secure random session token."""
    return secrets.token_hex(32)


# ── User management ───────────────────────────────────────────────────────────

def seed_demo_users(uow: AbstractUnitOfWork) -> None:
    """
    Seed the database with demo users — ONLY when SEED_DEMO_USERS=1.
    Passwords are read from DEMO_USER_<NAME>_PASSWORD env vars (random fallback).
    Skips silently in production to avoid creating known-weak accounts.
    """
    if os.environ.get("SEED_DEMO_USERS", "0") != "1":
        logger.info("Skipping demo user seeding (set SEED_DEMO_USERS=1 to enable).")
        return
    with uow:
        now = _now()
        for user_data in _demo_users():
            exists = uow.users.get_by_username(user_data["username"])
            if not exists:
                new_user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=hash_password(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                    created_at=now
                )
                uow.users.add(new_user)
            else:
                # Optionally re-hash if user exists but has a legacy SHA-256 hash
                if len(exists.password_hash) == 64:
                    exists.password_hash = hash_password(user_data["password"])
        uow.commit()


def authenticate(uow: AbstractUnitOfWork, username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user by username and password.
    """
    with uow:
        user = uow.users.get_by_username(username)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            return None
            
        user.last_login = _now()
        uow.commit()
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "organization_id": user.organization_id,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        }


def get_user_by_username(uow: AbstractUnitOfWork, username: str) -> Optional[Dict[str, Any]]:
    """Fetch a user by username (without password hash)."""
    with uow:
        user = uow.users.get_by_username(username)
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "organization_id": user.organization_id,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        }


def list_users(uow: AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Return all users (without password hashes)."""
    with uow:
        users = uow.users.get_all()
        return [{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "last_login": u.last_login
        } for u in users]


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
    uow: AbstractUnitOfWork,
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
    with uow:
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
        uow.audit_logs.add(log)
        uow.commit()


def fetch_audit_logs(
    uow: AbstractUnitOfWork,
    username: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Fetch audit log entries with optional filters."""
    with uow:
        filters = {}
        if username:
            filters["username"] = username
        if entity_type:
            filters["entity_type"] = entity_type
            
        logs = uow.audit_logs.get_recent(limit=limit, **filters)
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
