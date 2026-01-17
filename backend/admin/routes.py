"""
BioMind Nexus - Admin API Routes

Admin-only endpoints for system management:
- Audit log viewing
- User management
- Session revocation

All routes require ADMIN role.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlmodel import select

from backend.auth.models import User, Role, Session
<<<<<<< HEAD
from backend.auth.dependencies import get_current_user, AuthenticatedUser
=======
from backend.auth.dependencies import get_current_user
>>>>>>> fe0c4a4328d94727346608a580d888140836f2cd
from backend.auth.database import get_session


router = APIRouter()


# =============================================================================
# Dependencies
# =============================================================================

async def require_admin(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Require admin role for access."""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user


# =============================================================================
# Request/Response Models
# =============================================================================

class AuditLogEntry(BaseModel):
    """Single audit log entry."""
    event_id: str
    timestamp: str
    event_type: str
    user_id: str
    user_email: Optional[str] = None
    action: str
    request_id: Optional[str] = None
    details: dict = {}


class AuditLogResponse(BaseModel):
    """Paginated audit log response."""
    logs: List[AuditLogEntry]
    total: int
    page: int
    page_size: int


class UserListItem(BaseModel):
    """User item for admin list."""
    id: str
    email: str
    role: str
    is_active: bool
    created_at: str
    last_login: Optional[str] = None


class UserListResponse(BaseModel):
    """User list response."""
    users: List[UserListItem]
    total: int


class UserUpdateRequest(BaseModel):
    """Request to update user."""
    is_active: Optional[bool] = None
    role: Optional[str] = None


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    user_email: str
    issued_at: str
    expires_at: str
    last_seen: str
    ip_address: Optional[str] = None


class SessionListResponse(BaseModel):
    """Active sessions response."""
    sessions: List[SessionInfo]
    total: int


# =============================================================================
# Audit Log Endpoints
# =============================================================================

@router.get("/audit/logs", response_model=AuditLogResponse, summary="Get Audit Logs")
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=10, le=100, description="Items per page"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    filter_user_id: Optional[str] = Query(None, alias="user_id", description="Filter by user ID"),
    admin: AuthenticatedUser = Depends(require_admin)
):
    """
    Retrieve audit logs from Cassandra.
    
    Admin only. Supports pagination and filtering.
    """
    from backend.dal.cassandra_dal import get_cassandra_client
    
    client = get_cassandra_client()
    
    if not client:
        # Fallback to empty if Cassandra not available
        return AuditLogResponse(logs=[], total=0, page=page, page_size=page_size)
    
    try:
        # Build query
        query_parts = ["SELECT * FROM audit_events"]
        filters = []
        
        if event_type:
            filters.append(f"event_type = '{event_type}'")
        if filter_user_id:
            filters.append(f"user_id = '{filter_user_id}'")
        
        if filters:
            query_parts.append("WHERE " + " AND ".join(filters))
            query_parts.append("ALLOW FILTERING")
        
        query_parts.append(f"LIMIT {page_size * page}")
        query = " ".join(query_parts)
        
        # Execute query
        logs = []
        if hasattr(client, '_session') and client._session:
            from cassandra.query import SimpleStatement
            import json
            
            stmt = SimpleStatement(query)
            rows = client._session.execute(stmt)
            
            # Skip to the right page
            skip = (page - 1) * page_size
            count = 0
            
            for row in rows:
                count += 1
                if count <= skip:
                    continue
                if len(logs) >= page_size:
                    break
                
                # Parse details
                details = {}
                if row.details:
                    try:
                        details = json.loads(row.details)
                    except:
                        pass
                
                logs.append(AuditLogEntry(
                    event_id=str(row.event_id) if hasattr(row, 'event_id') else "",
                    timestamp=row.created_at.isoformat() if row.created_at else "",
                    event_type=row.event_type or "",
                    user_id=row.user_id or "",
                    action=row.action or "",
                    request_id=row.request_id if hasattr(row, 'request_id') else None,
                    details=details
                ))
        
        return AuditLogResponse(
            logs=logs,
            total=len(logs),  # Approximate
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        print(f"Audit query error: {e}")
        return AuditLogResponse(logs=[], total=0, page=page, page_size=page_size)


# =============================================================================
# User Management Endpoints
# =============================================================================

@router.get("/users", response_model=UserListResponse, summary="List All Users")
async def list_users(
    admin: AuthenticatedUser = Depends(require_admin),
    db=Depends(get_session)
):
    """
    List all users in the system.
    
    Admin only.
    """
    async with db as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        user_list = []
        for user in users:
            # Get last login from most recent session
            session_result = await session.execute(
                select(Session)
                .where(Session.user_id == user.id)
                .order_by(Session.issued_at.desc())
                .limit(1)
            )
            last_session = session_result.scalar_one_or_none()
            
            user_list.append(UserListItem(
                id=str(user.id),
                email=user.email,
                role=user.role.value if hasattr(user.role, 'value') else str(user.role),
                is_active=user.is_active,
                created_at=user.created_at.isoformat() if user.created_at else "",
                last_login=last_session.issued_at.isoformat() if last_session else None
            ))
        
        return UserListResponse(users=user_list, total=len(user_list))


@router.put("/users/{target_user_id}", summary="Update User")
async def update_user(
    target_user_id: str = Path(..., description="User ID to update"),
    update: UserUpdateRequest = None,
    admin: AuthenticatedUser = Depends(require_admin),
    db=Depends(get_session)
):
    """
    Update user status or role.
    
    Admin only. Used for activating/deactivating users.
    """
    async with db as session:
        result = await session.execute(
            select(User).where(User.id == UUID(target_user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent self-deactivation
        if str(admin.user_id) == target_user_id and update and update.is_active == False:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate your own account"
            )
        
        # Update fields
        if update:
            if update.is_active is not None:
                user.is_active = update.is_active
            
            if update.role is not None:
                try:
                    user.role = Role(update.role)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid role: {update.role}"
                    )
        
        user.updated_at = datetime.utcnow()
        session.add(user)
        await session.commit()
        
        return {"message": "User updated", "user_id": target_user_id}


@router.post("/users/{target_user_id}/revoke-sessions", summary="Revoke User Sessions")
async def revoke_user_sessions(
    target_user_id: str = Path(..., description="User ID to revoke sessions for"),
    admin: AuthenticatedUser = Depends(require_admin),
    db=Depends(get_session)
):
    """
    Revoke all active sessions for a user.
    
    Admin only. Forces user to re-login.
    """
    async with db as session:
        result = await session.execute(
            select(Session)
            .where(Session.user_id == UUID(target_user_id))
            .where(Session.is_valid == True)
        )
        sessions_list = result.scalars().all()
        
        count = 0
        for sess in sessions_list:
            sess.is_valid = False
            session.add(sess)
            count += 1
        
        await session.commit()
        
        return {"message": f"Revoked {count} sessions", "user_id": target_user_id}


# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.get("/sessions", response_model=SessionListResponse, summary="List Active Sessions")
async def list_active_sessions(
    admin: AuthenticatedUser = Depends(require_admin),
    db=Depends(get_session)
):
    """
    List all active sessions across all users.
    
    Admin only.
    """
    async with db as session:
        # Get active, non-expired sessions
        result = await session.execute(
            select(Session, User)
            .join(User, Session.user_id == User.id)
            .where(Session.is_valid == True)
            .where(Session.expires_at > datetime.utcnow())
            .order_by(Session.last_seen.desc())
            .limit(100)
        )
        rows = result.all()
        
        sessions_list = []
        for sess, user in rows:
            sessions_list.append(SessionInfo(
                session_id=str(sess.session_id),
                user_email=user.email,
                issued_at=sess.issued_at.isoformat() if sess.issued_at else "",
                expires_at=sess.expires_at.isoformat() if sess.expires_at else "",
                last_seen=sess.last_seen.isoformat() if sess.last_seen else "",
                ip_address=sess.ip_address
            ))
        
        return SessionListResponse(sessions=sessions_list, total=len(sessions_list))


@router.delete("/sessions/{target_session_id}", summary="Revoke Single Session")
async def revoke_session(
<<<<<<< HEAD
    target_session_id: str = Path(..., description="Session ID to revoke"),
    admin: AuthenticatedUser = Depends(require_admin),
=======
    target_session_id: str,
    admin: User = Depends(require_admin),
>>>>>>> fe0c4a4328d94727346608a580d888140836f2cd
    db=Depends(get_session)
):
    """
    Revoke a specific session.
    
    Admin only.
    """
    async with db as session:
        result = await session.execute(
            select(Session).where(Session.session_id == UUID(target_session_id))
        )
        sess = result.scalar_one_or_none()
        
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        
        sess.is_valid = False
        session.add(sess)
        await session.commit()
        
        return {"message": "Session revoked", "session_id": target_session_id}
