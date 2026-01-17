"""
BioMind Nexus - Database Configuration

SQLModel database setup with connection pooling.
Supports PostgreSQL (production) and SQLite (development).

Usage:
    from backend.auth.database import get_engine, init_db
    
    engine = get_engine()
    init_db(engine)  # Creates tables
"""

from typing import Generator
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from backend.config import settings


def get_database_url() -> str:
    """
    Get database URL from settings.
    
    Returns:
        PostgreSQL or SQLite connection string
    """
    if hasattr(settings, "DATABASE_URL") and settings.DATABASE_URL:
        return settings.DATABASE_URL
    
    # Default to SQLite for local development
    return "sqlite:///./biomind.db"


def get_engine(database_url: str = None, echo: bool = False):
    """
    Create SQLAlchemy engine with appropriate configuration.
    
    Args:
        database_url: Override database URL
        echo: Log SQL statements
        
    Returns:
        SQLAlchemy Engine
    """
    url = database_url or get_database_url()
    
    if url.startswith("sqlite"):
        # SQLite configuration
        engine = create_engine(
            url,
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # PostgreSQL configuration with connection pooling
        engine = create_engine(
            url,
            echo=echo,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    
    return engine


def init_db(engine) -> None:
    """
    Initialize database tables.
    
    Creates all tables defined in SQLModel models.
    Safe to call multiple times (uses CREATE IF NOT EXISTS).
    """
    # Import models to register them with SQLModel
    from backend.auth.models import User, Session, RefreshToken
    
    SQLModel.metadata.create_all(engine)


def get_session_factory(engine):
    """
    Create a session factory bound to engine.
    
    Returns:
        Callable that creates new database sessions
    """
    def session_factory() -> Session:
        return Session(engine)
    
    return session_factory


def get_session(engine) -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.
    
    Yields:
        Database session (auto-closed after use)
    """
    with Session(engine) as session:
        yield session
