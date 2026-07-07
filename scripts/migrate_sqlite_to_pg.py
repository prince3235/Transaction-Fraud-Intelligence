import json
import sqlite3
from pathlib import Path
import sys

# Ensure src module is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import (
    PredictionLog, User, AuditLog, FraudCase, BusinessRule,
    ModelRegistry, DriftSnapshot, CustomerProfile, AnalystMetric, CopilotLog
)

# Hardcoded old sqlite path
SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "app_db" / "fraud_intelligence.db"

import os
# Read PG url from env, fallback to localhost default
PG_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fraud_intelligence")

def get_sqlite_conn():
    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row
    return con

def parse_json(val):
    if not val:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return val

def migrate_table(sqlite_cur, pg_session, table_name, model_class, json_cols=None):
    if json_cols is None:
        json_cols = []
        
    print(f"Migrating {table_name}...")
    sqlite_cur.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cur.fetchall()
    
    for row in rows:
        data = dict(row)
        for col in json_cols:
            if col in data:
                data[col] = parse_json(data[col])
                
        # Boolean conversion for sqlite (0/1 -> False/True)
        for col in data:
            if isinstance(data[col], int) and col in ["is_active", "is_production", "is_archived", "alert_triggered", "policy_override_applied", "is_cached"]:
                data[col] = bool(data[col])
                
        obj = model_class(**data)
        pg_session.add(obj)
        
    pg_session.commit()
    print(f"Migrated {len(rows)} rows for {table_name}.")

def main():
    if not SQLITE_PATH.exists():
        print(f"SQLite DB not found at {SQLITE_PATH}. Exiting.")
        return
        
    pg_engine = create_engine(PG_URL)
    SessionLocal = sessionmaker(bind=pg_engine)
    pg_session = SessionLocal()
    
    sqlite_con = get_sqlite_conn()
    sqlite_cur = sqlite_con.cursor()
    
    tables = [
        ("prediction_logs", PredictionLog, ["transaction_json", "policy_reasons_json", "alert_json"]),
        ("users", User, []),
        ("audit_logs", AuditLog, ["old_value_json", "new_value_json"]),
        ("fraud_cases", FraudCase, ["evidence_json", "notes_json", "timeline_json"]),
        ("business_rules", BusinessRule, []), # condition_json is now a string!
        ("model_registry", ModelRegistry, []),
        ("drift_snapshots", DriftSnapshot, []),
        ("customer_profiles", CustomerProfile, []),
        ("analyst_metrics", AnalystMetric, []),
        ("copilot_logs", CopilotLog, ["query_context_json"])
    ]
    
    try:
        for t_name, model_cls, j_cols in tables:
            try:
                migrate_table(sqlite_cur, pg_session, t_name, model_cls, j_cols)
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    print(f"Table {t_name} not found in SQLite, skipping.")
                else:
                    raise
    finally:
        pg_session.close()
        sqlite_con.close()
        
    print("Migration complete.")

if __name__ == "__main__":
    main()
