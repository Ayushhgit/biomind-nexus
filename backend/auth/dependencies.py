"""
BioMind Nexus - Security Dependencies

FastAPI dependencies for authentication and authorization.
Implements hybrid JWT + session validation with RBAC.

Usage:
    @app.get("/protected")
    async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
        ...
    
    @app.get("/admin-only")
    @require_permission(Permission.MANAGE_USERS)
    async def admin_route(user: AuthenticatedUser = Depends(get_current_user)):
        ...

Security:
- Every protected request validates both JWT AND session
- RBAC is deny-by-default
- All failures are logged for audit
"""

from enum import Enum
from functools import wraps
from typing import Optional, Set, Dict
from uuid import UUID
from pathlib import Path

import yaml
from fastapi import HTTPException, status, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlmodel import Session as DBSession

from backend.auth.tokens import verify_access_token, TokenPayload, InvalidTokenError
from backend.auth import sessions
from backend.auth.models import Role


# HTTP Bearer scheme for JWT extraction
security = HTTPBearer(auto_error=False)


class Permission(str, Enum):
    """
    Granular permissions for RBAC.
    
    Permissions follow resource:action pattern.
    """
    # Agent operations
    QUERY_AGENTS = "query:agents"
    INVOKE_LITERATURE_AGENT = "invoke:literature_agent"
    INVOKE_REASONING_AGENT = "invoke:reasoning_agent"
    INVOKE_SAFETY_AGENT = "invoke:safety_agent"
    
    # Graph operations
    READ_GRAPH = "read:graph"
    WRITE_GRAPH = "write:graph"
    
    # Audit operations
    READ_AUDIT = "read:audit"
    EXPORT_AUDIT = "export:audit"
    
    # Dossier operations
    GENERATE_DOSSIER = "generate:dossier"
    EXPORT_DOSSIER = "export:dossier"
    
    # User management (admin only)
    MANAGE_USERS = "manage:users"


class AuthenticatedUser(BaseModel):
    """
    Represents a validated, authenticated user.
    
    Available in route handlers via Depends(get_current_user).
    """
    user_id: UUID
    email: str
    role: Role
    session_id: UUID
    token_id: str  # jti for audit correlation
    
    class Config:
        from_attributes = True


class RBACPolicy:
    """
    Role-Based Access Control policy manager.
    
    Loads role-permission mappings from policies.yaml.
    Implements deny-by-default: only explicit grants are allowed.
    """
    
    _instance: Optional["RBACPolicy"] = None
    _policies: Dict[str, Set[str]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_policies()
        return cls._instance
    
    def _load_policies(self):
        """Load policies from YAML configuration."""
        policy_path = Path(__file__).parent.parent / "gateway" / "policies.yaml"
        
        if not policy_path.exists():
            # Default deny-all if no policy file
            self._policies = {}
            return
        
        with open(policy_path, "r") as f:
            config = yaml.safe_load(f)
        
        self._policies = {
            role: set(perms)
            for role, perms in config.get("roles", {}).items()
        }
    
    def has_permission(self, role: str, permission: Permission) -> bool:
        """
        Check if a role has a specific permission.
        
        Args:
            role: User's role
            permission: Required permission
            
        Returns:
            True if permitted, False otherwise (deny-by-default)
        """
        role_perms = self._policies.get(role, set())
        return permission.value in role_perms
    
    def get_role_permissions(self, role: str) -> Set[str]:
        """Get all permissions for a role."""
        return self._policies.get(role, set())


# Database session dependency (to be provided by app)
async def get_db() -> DBSession:
    """
    Dependency to get database session.
    
    Must be overridden in app configuration.
    """
    raise NotImplementedError("Database session dependency not configured")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> AuthenticatedUser:
    """
    Validate request authentication and return current user.
    
    This dependency performs:
    1. Extract JWT from Authorization header
    2. Validate JWT signature and expiry
    3. Extract session ID from X-Session-ID header
    4. Validate session is active in database
    5. Return authenticated user
    
    Args:
        request: FastAPI request object
        credentials: JWT from Authorization header
        session_id: Session ID from X-Session-ID header
        
    Returns:
        AuthenticatedUser with validated claims
        
    Raises:
        HTTPException 401: Missing or invalid credentials
        HTTPException 401: Session invalid or expired
    """
    # Check Authorization header
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check Session ID header
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate JWT
    try:
        token_payload = verify_access_token(credentials.credentials)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate session ID matches token
    if token_payload.sid != session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session mismatch",
        )
    
    # Validate session in database
    try:
        db = request.app.state.db_session_factory()
        session_uuid = UUID(session_id)
        user_uuid = UUID(token_payload.sub)
        
        session = await sessions.validate_session(db, session_uuid, user_uuid)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
            )
        
        # Get user details from session
        user = session.user
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )
        
        return AuthenticatedUser(
            user_id=user.id,
            email=user.email,
            role=user.role,
            session_id=session_uuid,
            token_id=token_payload.jti,
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session format",
        )
    finally:
        db.close()


def require_permission(permission: Permission):
    """
    Decorator to enforce permission requirements on routes.
    
    Usage:
        @app.get("/admin-only")
        @require_permission(Permission.MANAGE_USERS)
        async def admin_route(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    
    Args:
        permission: Required permission
        
    Raises:
        HTTPException 403: If user lacks required permission
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (injected by Depends)
            user: Optional[AuthenticatedUser] = kwargs.get("user")
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            policy = RBACPolicy()
            if not policy.has_permission(user.role.value, permission):
                # Log permission denial for audit
                # TODO: Integrate with audit service
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}",
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions: Permission):
    """
    Decorator requiring at least one of the specified permissions.
    
    Usage:
        @require_any_permission(Permission.READ_GRAPH, Permission.READ_AUDIT)
        async def view_data(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user: Optional[AuthenticatedUser] = kwargs.get("user")
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            policy = RBACPolicy()
            has_any = any(
                policy.has_permission(user.role.value, perm)
                for perm in permissions
            )
            
            if not has_any:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of: {[p.value for p in permissions]}",
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: Role):
    """
    Decorator requiring a specific role.
    
    Usage:
        @require_role(Role.ADMIN)
        async def admin_only(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user: Optional[AuthenticatedUser] = kwargs.get("user")
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            if user.role != role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires role: {role.value}",
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
