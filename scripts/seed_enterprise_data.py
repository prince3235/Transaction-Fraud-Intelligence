"""
Enterprise Data Seeder.

Populates the database with realistic demo data for:
- Fraud cases with full investigation timelines
- Analyst actions and audit logs
- Business rules (seeded from rules_engine)
- Demo users (seeded from auth)
- Model registry v1 entry

Run once before demo: python scripts/seed_enterprise_data.py
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.db_migrations import run_migrations
from src.auth import seed_demo_users, log_audit_event, hash_password
from src.rules_engine import seed_default_rules
from src.storage import get_db_path
import sqlite3

DB_PATH = get_db_path(PROJECT_ROOT)

ANALYSTS = ["analyst", "compliance", "admin"]
STATUSES = ["Open", "Investigating", "Escalated", "Resolved", "False_Positive"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]

SAMPLE_TITLES = [
    "Suspicious TRANSFER — Account Drained",
    "High-Velocity ATM Withdrawal Pattern",
    "Potential Account Takeover — New Device",
    "Large TRANSFER to Zero-Balance Account",
    "Dormant Account Reactivation with Large Sum",
    "Cross-Border Transfer to High-Risk Region",
    "Multiple Failed then Successful Transfers",
    "Balance Mismatch Detected Post-Transfer",
    "Crypto Exchange — Layering Suspected",
    "Round-Amount Transfers — Structuring Pattern",
]

SAMPLE_NOTES = [
    "Initial review completed. Transaction pattern consistent with account takeover.",
    "Verified with customer via secondary channel. Transaction disputed.",
    "Cross-referenced with blacklisted account database. Match found.",
    "Escalated to Tier-2 review team for further investigation.",
    "Customer confirmed they did not initiate this transaction.",
    "Velocity analysis shows 5 similar transactions in 2-hour window.",
    "Device fingerprint does not match known customer devices.",
    "IP geolocation inconsistent with customer's registered address.",
]


def _rand_past(days: int = 30) -> str:
    delta = random.randint(0, days * 24 * 60)
    dt = datetime.now(timezone.utc) - timedelta(minutes=delta)
    return dt.isoformat()


def seed_fraud_cases(db_path: Path, count: int = 25) -> None:
    """Seed fraud cases with realistic investigation timelines."""
    import sqlite3
    con = sqlite3.connect(db_path, check_same_thread=False)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM fraud_cases")
    existing = cur.fetchone()[0]
    if existing >= count:
        print(f"  [skip] fraud_cases already has {existing} rows")
        con.close()
        return

    cur.execute("SELECT id FROM prediction_logs LIMIT 200")
    log_ids = [row[0] for row in cur.fetchall()] or [None]

    year = datetime.now(timezone.utc).year
    cur.execute(f"SELECT COUNT(*) FROM fraud_cases WHERE case_id LIKE 'FCS-{year}-%'")
    start_idx = cur.fetchone()[0]

    for i in range(count - existing):
        idx = start_idx + i + 1
        case_id = f"FCS-{year}-{idx:06d}"
        created = _rand_past(30)
        updated = created
        priority = random.choice(PRIORITIES)
        status = random.choice(STATUSES)
        title = random.choice(SAMPLE_TITLES)
        assigned = random.choice(ANALYSTS + [None])
        log_id = random.choice(log_ids)

        resolved_at = None
        if status in ("Resolved", "False_Positive"):
            resolved_at = _rand_past(5)

        notes = []
        for j in range(random.randint(1, 3)):
            notes.append({
                "id": j + 1,
                "author": random.choice(ANALYSTS),
                "content": random.choice(SAMPLE_NOTES),
                "timestamp": _rand_past(10),
            })

        timeline = [
            {
                "timestamp": created,
                "actor": "system",
                "action": "Case Created",
                "from_status": None,
                "to_status": "Open",
                "note": f"Auto-created from alert. Priority: {priority}",
            }
        ]
        if status != "Open":
            timeline.append({
                "timestamp": _rand_past(20),
                "actor": random.choice(ANALYSTS),
                "action": "Status Updated",
                "from_status": "Open",
                "to_status": status,
                "note": f"Moved to {status} after initial review.",
            })

        cur.execute(
            """
            INSERT INTO fraud_cases
                (case_id, prediction_log_id, status, priority, assigned_to,
                 title, description, evidence_json, notes_json, timeline_json,
                 created_at, updated_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                log_id,
                status,
                priority,
                assigned,
                title,
                f"Investigation case for {title.lower()}. Requires analyst review.",
                json.dumps(notes),
                json.dumps(timeline),
                created,
                updated,
                resolved_at,
            ),
        )

    con.commit()
    con.close()
    print(f"  [ok] Seeded {count - existing} fraud cases")


def seed_audit_logs(db_path: Path, count: int = 50) -> None:
    """Seed realistic audit log entries."""
    con = sqlite3.connect(db_path, check_same_thread=False)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM audit_logs")
    existing = cur.fetchone()[0]
    if existing >= count:
        print(f"  [skip] audit_logs already has {existing} rows")
        con.close()
        return

    actions = [
        ("Login", "auth", None),
        ("Case Status Updated", "fraud_case", "FCS-2024-000001"),
        ("Rule Toggled", "business_rule", "1"),
        ("Transaction Approved", "prediction_log", "42"),
        ("Transaction Blocked", "prediction_log", "17"),
        ("Note Added", "fraud_case", "FCS-2024-000002"),
        ("Model Retrained", "model_registry", "v1"),
        ("Data Exported", "export", "CSV"),
        ("Case Assigned", "fraud_case", "FCS-2024-000003"),
        ("User Login Failed", "auth", None),
    ]

    for i in range(count - existing):
        actor = random.choice(ANALYSTS)
        action, etype, eid = random.choice(actions)
        cur.execute(
            """
            INSERT INTO audit_logs
                (username, action, entity_type, entity_id,
                 old_value_json, new_value_json, ip_address, reason, timestamp)
            VALUES (?, ?, ?, ?, NULL, NULL, ?, NULL, ?)
            """,
            (actor, action, etype, eid, "127.0.0.1", _rand_past(30)),
        )

    con.commit()
    con.close()
    print(f"  [ok] Seeded {count - existing} audit log entries")


def seed_model_registry(db_path: Path) -> None:
    """Seed v1 model registry entry based on existing model file."""
    con = sqlite3.connect(db_path, check_same_thread=False)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM model_registry")
    if cur.fetchone()[0] > 0:
        print("  [skip] model_registry already seeded")
        con.close()
        return

    pkl_path = str(PROJECT_ROOT / "models" / "best_fraud_model.pkl")
    cur.execute(
        """
        INSERT INTO model_registry
            (version, pkl_path, roc_auc, pr_auc, precision_val, recall_val, f1_val,
             n_estimators, training_date, dataset_size, feature_count, notes,
             is_production, is_archived, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
        """,
        (
            "v1",
            pkl_path,
            0.9987,
            0.9812,
            0.9341,
            0.8876,
            0.9103,
            100,
            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            9600,
            29,
            "Initial production model. RandomForest with balance error features.",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    con.commit()
    con.close()
    print("  [ok] Seeded model registry v1")


if __name__ == "__main__":
    print("Starting enterprise data seeding...")
    print(f"  DB: {DB_PATH}")

    print("\n[1/6] Running migrations...")
    run_migrations(DB_PATH)
    print("  [ok] Migrations complete")

    print("\n[2/6] Seeding demo users...")
    seed_demo_users(DB_PATH)
    print("  [ok] Demo users seeded")

    print("\n[3/6] Seeding business rules...")
    seed_default_rules(DB_PATH)
    print("  [ok] Business rules seeded")

    print("\n[4/6] Seeding fraud cases...")
    seed_fraud_cases(DB_PATH, count=25)

    print("\n[5/6] Seeding audit logs...")
    seed_audit_logs(DB_PATH, count=50)

    print("\n[6/6] Seeding model registry...")
    seed_model_registry(DB_PATH)

    print("\n[ok] Enterprise seeding complete!")
    print("\nDemo credentials:")
    print("  admin / admin123        (Full access)")
    print("  analyst / analyst123    (Analyst access)")
    print("  compliance / comply123  (Compliance Officer)")
    print("  auditor / audit123      (Read-only audit)")
    print("  viewer / view123        (Dashboard only)")
