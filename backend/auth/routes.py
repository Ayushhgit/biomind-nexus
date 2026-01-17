"""
BioMind Nexus - Authentication Routes

API endpoints for authentication:
- POST /auth/login     - Authenticate and create session
- POST /auth/logout    - Invalidate session
- POST /auth/refresh   - Refresh access token
- GET  /auth/me        - Get current user info
- GET  /auth/sessions  - List active sessions

All operations are logged to audit trail.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Request, Header
from sqlmodel import Session as DBSession, select

from backend.auth.models import User, Session, Role
from backend.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    UserResponse,
    ActiveSessionsResponse,
    SessionInfo,
    CreateUserRequest,
    CreateUserResponse,
    ErrorResponse,
)
from backend.auth.password import verify_password, hash_password, needs_rehash
from backend.auth.tokens import create_access_token, get_token_expiry_seconds
from backend.auth import sessions as session_service
from backend.auth.dependencies import (
    get_current_user,
    AuthenticatedUser,
    require_permission,
    require_role,
    Permission,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


def get_db(request: Request) -> DBSession:
    """Get database session from app state."""
    return request.app.state.db_session_factory()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request."""
    return request.headers.get("User-Agent", "unknown")[:512]


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Authenticate user and create session",
)
async def login(
    request: Request,
    credentials: LoginRequest,
):
    """
    Authenticate user with email and password.
    
    On successful authentication:
    1. Validates password against bcrypt hash
    2. Creates server-side session
    3. Issues JWT access token bound to session
    4. Logs authentication event to audit trail
    
    Returns:
        LoginResponse with access_token and session_id
        
    Raises:
        401: Invalid credentials or inactive account
    """
    db = get_db(request)
    
    try:
        # Find user by email
        statement = select(User).where(User.email == credentials.email)
        user = db.exec(statement).first()
        
        if not user:
            # Log failed attempt (no user)
            await _log_auth_event(
                request, "auth.login.failure",
                details={"email": credentials.email, "reason": "user_not_found"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        
        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            await _log_auth_event(
                request, "auth.login.failure",
                user_id=str(user.id),
                details={"reason": "invalid_password"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        
        # Check if user is active
        if not user.is_active:
            await _log_auth_event(
                request, "auth.login.failure",
                user_id=str(user.id),
                details={"reason": "account_inactive"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
            )
        
        # Check if password needs rehash (work factor upgrade)
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(credentials.password)
            db.add(user)
            db.commit()
        
        # Create server-side session
        session = await session_service.create_session(
            db=db,
            user_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        # Create access token
        access_token, token_id = create_access_token(
            user_id=user.id,
            role=user.role.value,
            session_id=session.session_id,
        )
        
        # Log successful login
        await _log_auth_event(
            request, "auth.login.success",
            user_id=str(user.id),
            details={
                "session_id": str(session.session_id),
                "token_id": token_id,
            }
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_expiry_seconds(),
            session_id=str(session.session_id),
        )
        
    finally:
        db.close()


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Invalidate current session",
)
async def logout(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    body: Optional[LogoutRequest] = None,
):
    """
    Invalidate the current session (or all sessions).
    
    After logout:
    - Session is marked invalid in database
    - All JWT tokens bound to this session become invalid
    - Subsequent requests with this token/session will fail
    
    Args:
        body: Optional. Set all_sessions=true to logout everywhere.
        
    Returns:
        LogoutResponse with count of invalidated sessions
    """
    db = get_db(request)
    
    try:
        if body and body.all_sessions:
            # Invalidate all sessions for user
            count = await session_service.invalidate_all_user_sessions(db, user.user_id)
            
            await _log_auth_event(
                request, "auth.logout.all",
                user_id=str(user.user_id),
                details={"sessions_invalidated": count}
            )
            
            return LogoutResponse(
                message="All sessions invalidated",
                sessions_invalidated=count,
            )
        else:
            # Invalidate current session only
            await session_service.invalidate_session(db, user.session_id)
            
            await _log_auth_event(
                request, "auth.logout",
                user_id=str(user.user_id),
                details={"session_id": str(user.session_id)}
            )
            
            return LogoutResponse(
                message="Session invalidated",
                sessions_invalidated=1,
            )
            
    finally:
        db.close()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
)
async def get_me(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get the current authenticated user's profile.
    
    Returns:
        UserResponse with user details
    """
    db = get_db(request)
    
    try:
        statement = select(User).where(User.id == user.user_id)
        db_user = db.exec(statement).first()
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        return UserResponse(
            id=db_user.id,
            email=db_user.email,
            role=db_user.role.value,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
        )
        
    finally:
        db.close()


@router.get(
    "/sessions",
    response_model=ActiveSessionsResponse,
    summary="List active sessions",
)
async def list_sessions(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    session_id: str = Header(alias="X-Session-ID"),
):
    """
    List all active sessions for the current user.
    
    Returns:
        List of sessions with metadata
    """
    db = get_db(request)
    
    try:
        active_sessions = await session_service.get_active_sessions(db, user.user_id)
        
        session_list = []
        for s in active_sessions:
            session_list.append(SessionInfo(
                session_id=s.session_id,
                issued_at=s.issued_at,
                last_seen=s.last_seen,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                is_current=(str(s.session_id) == session_id),
            ))
        
        return ActiveSessionsResponse(
            sessions=session_list,
            total=len(session_list),
        )
        
    finally:
        db.close()


@router.delete(
    "/sessions/{target_session_id}",
    response_model=LogoutResponse,
    summary="Revoke a specific session",
)
async def revoke_session(
    request: Request,
    target_session_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Revoke a specific session.
    
    Users can only revoke their own sessions.
    Admins can revoke any session.
    """
    db = get_db(request)
    
    try:
        # Verify session belongs to user (or user is admin)
        statement = select(Session).where(Session.session_id == target_session_id)
        session = db.exec(statement).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        
        if session.user_id != user.user_id and user.role != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot revoke another user's session",
            )
        
        await session_service.invalidate_session(db, target_session_id)
        
        await _log_auth_event(
            request, "auth.session.revoked",
            user_id=str(user.user_id),
            details={
                "target_session_id": str(target_session_id),
                "target_user_id": str(session.user_id),
            }
        )
        
        return LogoutResponse(
            message="Session revoked",
            sessions_invalidated=1,
        )
        
    finally:
        db.close()


@router.post(
    "/users",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user (admin only)",
)
@require_permission(Permission.MANAGE_USERS)
async def create_user(
    request: Request,
    body: CreateUserRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Create a new user account.
    
    Admin only. Password is hashed with bcrypt.
    """
    db = get_db(request)
    
    try:
        # Check if email already exists
        statement = select(User).where(User.email == body.email)
        existing = db.exec(statement).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        
        # Create user
        now = datetime.utcnow()
        new_user = User(
            email=body.email,
            password_hash=hash_password(body.password),
            role=Role(body.role),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        await _log_auth_event(
            request, "auth.user.created",
            user_id=str(user.user_id),
            details={
                "new_user_id": str(new_user.id),
                "new_user_email": new_user.email,
                "new_user_role": new_user.role.value,
            }
        )
        
        return CreateUserResponse(
            id=new_user.id,
            email=new_user.email,
            role=new_user.role.value,
            created_at=new_user.created_at,
        )
        
    finally:
        db.close()


async def _log_auth_event(
    request: Request,
    event_type: str,
    user_id: Optional[str] = None,
    details: Optional[dict] = None,
):
    """
    Log authentication event to audit trail.
    
    Uses cassandra_dal which has file-based fallback.
    """
    try:
        from backend.dal.cassandra_dal import log_workflow_event
        import uuid
        
        await log_workflow_event(
            request_id=str(uuid.uuid4()),
            user_id=user_id or "anonymous",
            event_type=event_type,
            agent_name=event_type.split(".")[-1],
            input_hash="",
            output_hash="",
            step_index=0,
            metadata={
                **(details or {}),
                "ip": get_client_ip(request),
                "user_agent": get_user_agent(request)[:256],
            }
        )
    except Exception as e:
        # Don't fail request if audit logging fails
        print(f"Audit logging error: {e}")
        pass
