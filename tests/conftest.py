import os
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base

@pytest.fixture(scope="session")
def postgres_container():
    """Start a Postgres container for the test session if Docker is available and not in CI."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # In GitHub Actions, we use the service container defined in the workflow
        # The DATABASE_URL is already provided via env var.
        yield None
        return
        
    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
        os.environ["DATABASE_URL"] = container.get_connection_url()
        yield container
        container.stop()
    except Exception as e:
        # Docker not available, fallback to SQLite
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        yield None

@pytest.fixture(scope="session")
def engine(postgres_container):
    """Create a SQLAlchemy engine connected to the test container or SQLite fallback."""
    # postgres_container will be None if in CI or if Docker is unavailable.
    db_url = os.environ.get("DATABASE_URL")
    
    if db_url and not db_url.startswith("sqlite"):
        engine = create_engine(db_url)
    else:
        from sqlalchemy.pool import StaticPool
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
    # Create all tables in the test database
    Base.metadata.create_all(bind=engine)
    yield engine
    # Drop all tables after tests
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine):
    """Provide a transactional scoped session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def override_sessionlocal(db_session, monkeypatch):
    """Monkeypatch src.db.SessionLocal to return our test db_session."""
    import src.db
    monkeypatch.setattr(src.db, "SessionLocal", lambda: db_session)
