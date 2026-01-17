"""
BioMind Nexus - Authentication Module

Handles JWT-based authentication for local development.
All tokens are stateless and validated on each request.

Security:
- Tokens expire after configured duration
- No session storage (stateless)
- All auth events are logged to audit trail
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from backend.config import settings


security = HTTPBearer()


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # User ID
    role: str  # User role for RBAC
    exp: datetime
    iat: datetime
    jti: str  # Unique token ID for audit


class AuthenticatedUser(BaseModel):
    """Represents a validated, authenticated user."""
    user_id: str
    role: str
    token_id: str


def create_access_token(user_id: str, role: str) -> str:
    """
    Create a new JWT access token.
    
    Args:
        user_id: Unique identifier for the user
        role: User's RBAC role
    
    Returns:
        Encoded JWT string
    
    Security: Token includes unique JTI for audit trail correlation.
    """
    now = datetime.utcnow()
    token_id = secrets.token_hex(16)
    
    payload = {
        "sub": user_id,
        "role": role,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "jti": token_id,
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> TokenPayload:
    """
    Verify and decode a JWT token.
    
    Args:
        token: Encoded JWT string
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return TokenPayload(**payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthenticatedUser:
    """
    FastAPI dependency to extract and validate current user from request.
    
    Returns:
        AuthenticatedUser with validated claims
    
    Raises:
        HTTPException: If authentication fails
    """
    token_payload = verify_token(credentials.credentials)
    
    return AuthenticatedUser(
        user_id=token_payload.sub,
        role=token_payload.role,
        token_id=token_payload.jti,
    )


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password using SHA-256 with salt.
    
    For local development only. Production should use bcrypt/argon2.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
    
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    combined = f"{salt}:{password}"
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    
    return hashed, salt
