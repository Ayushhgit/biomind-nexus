"""
BioMind Nexus - Authentication Request/Response Schemas

Pydantic models for API request validation and response serialization.
Separates API contracts from database models.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, validator
import re


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    
    @validator("email")
    def email_format(cls, v):
        """Basic email format validation (allows .local for development)."""
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()
    
    @validator("password")
    def password_complexity(cls, v):
        """Ensure password meets minimum complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginResponse(BaseModel):
    """Response body for successful login."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until token expires")
    session_id: str = Field(..., description="Session ID for X-Session-ID header")


class LogoutRequest(BaseModel):
    """Request body for POST /auth/logout (optional)."""
    all_sessions: bool = Field(
        default=False,
        description="Invalidate all sessions (logout everywhere)"
    )


class LogoutResponse(BaseModel):
    """Response body for logout."""
    message: str = Field(default="Session invalidated")
    sessions_invalidated: int = Field(default=1)


class RefreshRequest(BaseModel):
    """Request body for POST /auth/refresh."""
    refresh_token: str = Field(..., description="Refresh token")


class RefreshResponse(BaseModel):
    """Response body for token refresh."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Response body for GET /auth/me."""
    id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    """Session information for user display."""
    session_id: UUID
    issued_at: datetime
    last_seen: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_current: bool = False
    
    class Config:
        from_attributes = True


class ActiveSessionsResponse(BaseModel):
    """Response body for GET /auth/sessions."""
    sessions: list[SessionInfo]
    total: int


class CreateUserRequest(BaseModel):
    """Request body for POST /auth/users (admin only)."""
    email: str
    password: str = Field(..., min_length=8)
    role: str = Field(default="researcher")
    
    @validator("email")
    def email_format(cls, v):
        """Basic email format validation (allows .local for development)."""
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()
    
    @validator("role")
    def valid_role(cls, v):
        valid_roles = {"admin", "researcher", "reviewer", "auditor"}
        if v not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")
        return v
    
    @validator("password")
    def password_strength(cls, v):
        """Enforce password strength requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class CreateUserResponse(BaseModel):
    """Response body for user creation."""
    id: UUID
    email: str
    role: str
    created_at: datetime


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None
    request_id: Optional[str] = None
