"""
BioMind Nexus - Test Configuration

Pytest fixtures for authentication testing.
Provides test database, client, and user fixtures.
"""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4
from typing import Generator

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from backend.app import app
from backend.auth.database import get_session_factory
from backend.auth.models import User, Role
from backend.auth.password import hash_password


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_engine():
    """Create a fresh test database engine for each test."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Import models to register them
    from backend.auth.models import User, Session, RefreshToken
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(test_engine) -> Generator[TestClient, None, None]:
    """Create a test client with fresh database."""
    # Configure app to use test database
    app.state.db_engine = test_engine
    app.state.db_session_factory = get_session_factory(test_engine)
    
    # Disable external services
    app.state.neo4j = None
    app.state.audit = None
    
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def test_admin(db_session) -> User:
    """Create a test admin user."""
    now = datetime.utcnow()
    user = User(
        id=uuid4(),
        email="admin@test.com",
        password_hash=hash_password("AdminPass123"),
        role=Role.ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_researcher(db_session) -> User:
    """Create a test researcher user."""
    now = datetime.utcnow()
    user = User(
        id=uuid4(),
        email="researcher@test.com",
        password_hash=hash_password("ResearchPass123"),
        role=Role.RESEARCHER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_auditor(db_session) -> User:
    """Create a test auditor user."""
    now = datetime.utcnow()
    user = User(
        id=uuid4(),
        email="auditor@test.com",
        password_hash=hash_password("AuditPass123"),
        role=Role.AUDITOR,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def inactive_user(db_session) -> User:
    """Create an inactive test user."""
    now = datetime.utcnow()
    user = User(
        id=uuid4(),
        email="inactive@test.com",
        password_hash=hash_password("InactivePass123"),
        role=Role.RESEARCHER,
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login_user(client: TestClient, email: str, password: str) -> dict:
    """Helper function to login and return tokens."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response.json() if response.status_code == 200 else None


def auth_headers(access_token: str, session_id: str) -> dict:
    """Create authorization headers for authenticated requests."""
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Session-ID": session_id,
    }
