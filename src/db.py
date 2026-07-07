import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Default to Postgres, fallback to SQLite for local tests if needed
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/app_db/fraud_intelligence.db")

# For SQLite, we need connect_args={"check_same_thread": False}
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
