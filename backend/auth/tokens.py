"""
BioMind Nexus - JWT Token Management

Creates and validates JWT access tokens with:
- User ID (sub)
- Role (for RBAC)
- Session ID (for server-side validation)
- Unique token ID (jti for audit correlation)

Security:
- Short-lived tokens (15 minutes default)
- All tokens include session ID for revocation
- jti enables audit trail correlation
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import secrets

from jose import jwt, JWTError
from pydantic import BaseModel, Field

from backend.config import settings


# Token configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 15


class TokenPayload(BaseModel):
    """
    JWT token payload structure.
    
    Attributes:
        sub: Subject (user ID)
        role: User role for RBAC
        sid: Session ID for server-side validation
        jti: Unique token ID for audit
        exp: Expiration timestamp
        iat: Issued-at timestamp
    """
    sub: str = Field(..., description="User ID")
    role: str = Field(..., description="User role")
    sid: str = Field(..., description="Session ID")
    jti: str = Field(..., description="Token ID for audit")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at time")


class TokenResponse(BaseModel):
    """Response model for login endpoint."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Seconds until expiration")
    session_id: str


def create_access_token(
    user_id: UUID,
    role: str,
    session_id: UUID,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, str]:
    """
    Create a new JWT access token.
    
    Args:
        user_id: User's unique identifier
        role: User's RBAC role
        session_id: Server-side session identifier
        expires_delta: Optional custom expiration time
        
    Returns:
        Tuple of (encoded JWT string, token ID)
        
    Security:
        - Token includes session_id for server-side revocation
        - jti is a cryptographically random ID for audit trail
        - Short expiration (15 min) limits token replay window
        
    Example:
        >>> token, jti = create_access_token(user_id, "researcher", session_id)
        >>> # Token is ready to send to client
        >>> # jti should be logged for audit correlation
    """
    now = datetime.utcnow()
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Generate unique token ID for audit trail
    token_id = secrets.token_hex(16)
    
    payload = {
        "sub": str(user_id),
        "role": role,
        "sid": str(session_id),
        "jti": token_id,
        "exp": expire,
        "iat": now,
    }
    
    encoded_jwt = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt, token_id


def verify_access_token(token: str) -> TokenPayload:
    """
    Verify and decode a JWT access token.
    
    Args:
        token: Encoded JWT string
        
    Returns:
        Decoded TokenPayload
        
    Raises:
        InvalidTokenError: If token is invalid, expired, or malformed
        
    Security:
        - Validates signature using SECRET_KEY
        - Checks expiration automatically
        - Returns structured payload for further validation
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return TokenPayload(**payload)
    except JWTError as e:
        raise InvalidTokenError(f"Token validation failed: {str(e)}")


class InvalidTokenError(Exception):
    """Raised when JWT validation fails."""
    pass


def get_token_expiry_seconds() -> int:
    """Get token expiry time in seconds for response."""
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60
