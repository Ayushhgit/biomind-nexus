"""
BioMind Nexus - Authentication Database Models

SQLModel-based models for user authentication and session management.
Uses PostgreSQL for production, SQLite for local development.

Security:
- Passwords stored as bcrypt hashes only
- Sessions are server-controlled for immediate revocation
- All timestamps in UTC
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum


class Role(str, Enum):
    """
    User roles for RBAC.
    
    Permissions are deny-by-default; each role has explicit grants.
    """
    ADMIN = "admin"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


class User(SQLModel, table=True):
    """
    User account for authentication.
    
    Attributes:
        id: Unique identifier (UUIDv4)
        email: Login identifier (unique, indexed)
        password_hash: bcrypt hash (never store plaintext)
        role: RBAC role determining permissions
        is_active: Soft-delete flag; inactive users cannot login
        created_at: Account creation timestamp (UTC)
        updated_at: Last modification timestamp (UTC)
    """
    __tablename__ = "users"
    
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique user identifier"
    )
    email: str = Field(
        sa_column=Column(String(255), unique=True, index=True, nullable=False),
        description="User email address (login identifier)"
    )
    password_hash: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="bcrypt password hash"
    )
    role: Role = Field(
        sa_column=Column(SQLEnum(Role), nullable=False, default=Role.RESEARCHER),
        description="User role for RBAC"
    )
    is_active: bool = Field(
        sa_column=Column(Boolean, nullable=False, default=True),
        description="Whether user can authenticate"
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.utcnow),
        description="Account creation timestamp"
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        description="Last update timestamp"
    )
    
    # Relationships
    sessions: list["Session"] = Relationship(back_populates="user")


class Session(SQLModel, table=True):
    """
    Server-side session for authentication validation.
    
    JWT tokens are validated against active sessions.
    Revoking a session immediately invalidates all associated tokens.
    
    Attributes:
        session_id: Unique session identifier (UUIDv4)
        user_id: Foreign key to user
        issued_at: Session creation timestamp
        expires_at: Session expiration timestamp
        last_seen: Last activity timestamp (updated on each request)
        is_valid: Whether session is active (false after logout)
        ip_address: Client IP for audit
        user_agent: Client user-agent for audit
    """
    __tablename__ = "sessions"
    
    session_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique session identifier"
    )
    user_id: UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True,
        description="Reference to user"
    )
    issued_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.utcnow),
        description="Session creation timestamp"
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False),
        description="Session expiration timestamp"
    )
    last_seen: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.utcnow),
        description="Last activity timestamp"
    )
    is_valid: bool = Field(
        sa_column=Column(Boolean, nullable=False, default=True),
        description="Whether session is active"
    )
    ip_address: Optional[str] = Field(
        sa_column=Column(String(45), nullable=True),
        description="Client IP address"
    )
    user_agent: Optional[str] = Field(
        sa_column=Column(String(512), nullable=True),
        description="Client user-agent string"
    )
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="sessions")


class RefreshToken(SQLModel, table=True):
    """
    Refresh token for session extension.
    
    Allows issuing new access tokens without re-authentication.
    Implements token rotation for security.
    
    Attributes:
        token_id: Unique token identifier
        session_id: Associated session
        token_hash: SHA-256 hash of the token (never store plaintext)
        issued_at: Token creation timestamp
        expires_at: Token expiration timestamp
        is_used: Whether token has been consumed (one-time use)
        replaced_by: New token ID if rotated
    """
    __tablename__ = "refresh_tokens"
    
    token_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique token identifier"
    )
    session_id: UUID = Field(
        foreign_key="sessions.session_id",
        nullable=False,
        index=True,
        description="Reference to session"
    )
    token_hash: str = Field(
        sa_column=Column(String(64), nullable=False),
        description="SHA-256 hash of refresh token"
    )
    issued_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, default=datetime.utcnow),
        description="Token creation timestamp"
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False),
        description="Token expiration timestamp"
    )
    is_used: bool = Field(
        sa_column=Column(Boolean, nullable=False, default=False),
        description="Whether token has been consumed"
    )
    replaced_by: Optional[UUID] = Field(
        default=None,
        description="New token ID if rotated"
    )
