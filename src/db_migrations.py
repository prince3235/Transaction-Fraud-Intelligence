"""
Database Migration Manager.

Uses SQLAlchemy's create_all for idempotent schema creation.
For production schema changes, use Alembic.
"""
from __future__ import annotations
from pathlib import Path
from src.db import engine
from src.models import Base

def run_migrations(db_path: Path) -> None:
    """
    Execute schema initialization.
    
    This function is idempotent — safe to call on every application startup.
    It creates tables that do not exist yet.
    
    Args:
        db_path: Ignored, kept for compatibility.
    """
    Base.metadata.create_all(bind=engine)
