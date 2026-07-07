import os
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base

@pytest.fixture(scope="session")
def postgres_container():
    """Start a Postgres container for the test session."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        # Override the DATABASE_URL env var for the application
        os.environ["DATABASE_URL"] = postgres.get_connection_url()
        yield postgres

@pytest.fixture(scope="session")
def engine(postgres_container):
    """Create a SQLAlchemy engine connected to the test container."""
    engine = create_engine(postgres_container.get_connection_url())
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
