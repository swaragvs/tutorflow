"""Pytest configuration and fixtures for TutorFlow backend tests."""

import os
from typing import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.db.session import Base


@pytest.fixture(scope="session")
def test_db_url():
    """Get test database URL or use SQLite in-memory for local testing."""
    return os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(scope="session")
def test_engine(test_db_url):
    """Create a test database engine."""

    engine = create_engine(
        test_db_url,
        echo=False,
        connect_args={"check_same_thread": False}
        if "sqlite" in test_db_url
        else {},
    )

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


