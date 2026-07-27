from pathlib import Path
from sqlalchemy import text
from src.db import engine
from src.models import Base

def run_migrations(db_path: Path = None) -> None:
    """
    Execute schema initialization and column updates.
    Idempotent — safe to call on every startup.
    """
    Base.metadata.create_all(bind=engine)

    # Safely migrate new columns to existing SQLite/DB tables
    with engine.begin() as conn:
        tables = ["users", "prediction_logs", "fraud_cases", "business_rules", "audit_logs"]
        for table in tables:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN organization_id INTEGER"))
            except Exception:
                pass

