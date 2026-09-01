"""Pytest configuration and fixtures for TutorFlow backend tests."""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def test_db_url():
    """Get test database URL or use SQLite in-memory for local testing."""
    return os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(scope="session")
def test_engine(test_db_url):
    """Create a test database engine."""

    # For SQLite in-memory, use StaticPool to ensure all connections share the same DB
    engine_kwargs = {
        "echo": False,
    }
    
    if "sqlite" in test_db_url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(test_db_url, **engine_kwargs)

    # SQLite does not enforce foreign keys by default.
    if "sqlite" in test_db_url:

        @event.listens_for(engine, "connect")
        def set_sqlite_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)


@pytest.fixture
def db(test_engine) -> Generator[Session, None, None]:
    """Provide a completely clean database session for each test."""

    # Clean all data before each test.
    with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db: Session) -> TestClient:
    """
    Provide a TestClient that uses the test database.
    
    Overrides the get_db dependency so FastAPI routes query the test database
    instead of the production DATABASE_URL.
    """
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    test_client = TestClient(app)
    
    yield test_client
    
    # Clean up
    app.dependency_overrides.clear()



