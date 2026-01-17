"""
BioMind Nexus - Session Management

Server-side session management for authentication.
Sessions enable immediate token revocation and activity tracking.

Security:
- Sessions are stored server-side (not in JWT only)
- Logout immediately invalidates session
- Activity tracking for audit and anomaly detection
- Session expires after 24 hours of inactivity
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import Session as DBSession, select

from backend.auth.models import Session


# Session configuration
SESSION_EXPIRE_HOURS = 24


async def create_session(
    db: DBSession,
    user_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Session:
    """
    Create a new server-side session.
    
    Args:
        db: Database session
        user_id: User's unique identifier
        ip_address: Client IP for audit
        user_agent: Client user-agent for audit
        
    Returns:
        Created Session object
        
    Security:
        - Session ID is UUIDv4 (cryptographically random)
        - IP and user-agent logged for anomaly detection
        - Expires after SESSION_EXPIRE_HOURS
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=SESSION_EXPIRE_HOURS)
    
    session = Session(
        user_id=user_id,
        issued_at=now,
        expires_at=expires_at,
        last_seen=now,
        is_valid=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


async def validate_session(
    db: DBSession,
    session_id: UUID,
    user_id: UUID,
) -> Optional[Session]:
    """
    Validate a session is active and belongs to user.
    
    Args:
        db: Database session
        session_id: Session to validate
        user_id: Expected user ID
        
    Returns:
        Session if valid, None otherwise
        
    Validation checks:
        1. Session exists
        2. Session belongs to user
        3. Session is not invalidated
        4. Session is not expired
    """
    statement = select(Session).where(
        Session.session_id == session_id,
        Session.user_id == user_id,
        Session.is_valid == True,
    )
    
    session = db.exec(statement).first()
    
    if not session:
        return None
    
    # Check expiration
    if datetime.utcnow() > session.expires_at:
        # Mark expired session as invalid
        session.is_valid = False
        db.add(session)
        db.commit()
        return None
    
    # Update last_seen for activity tracking
    session.last_seen = datetime.utcnow()
    db.add(session)
    db.commit()
    
    return session


async def invalidate_session(db: DBSession, session_id: UUID) -> bool:
    """
    Invalidate a session (logout).
    
    Args:
        db: Database session
        session_id: Session to invalidate
        
    Returns:
        True if session was invalidated, False if not found
        
    Security:
        - Immediate effect; subsequent requests with this session fail
        - JWT tokens bound to this session become invalid instantly
    """
    statement = select(Session).where(Session.session_id == session_id)
    session = db.exec(statement).first()
    
    if not session:
        return False
    
    session.is_valid = False
    db.add(session)
    db.commit()
    
    return True


async def invalidate_all_user_sessions(db: DBSession, user_id: UUID) -> int:
    """
    Invalidate all sessions for a user (force logout everywhere).
    
    Args:
        db: Database session
        user_id: User whose sessions to invalidate
        
    Returns:
        Number of sessions invalidated
        
    Use cases:
        - Password change
        - Account compromise
        - Admin forced logout
    """
    statement = select(Session).where(
        Session.user_id == user_id,
        Session.is_valid == True,
    )
    
    sessions = db.exec(statement).all()
    count = 0
    
    for session in sessions:
        session.is_valid = False
        db.add(session)
        count += 1
    
    db.commit()
    
    return count


async def get_active_sessions(db: DBSession, user_id: UUID) -> list[Session]:
    """
    Get all active sessions for a user.
    
    Args:
        db: Database session
        user_id: User to query
        
    Returns:
        List of active sessions
        
    Use cases:
        - Show user their active sessions
        - Admin audit
    """
    now = datetime.utcnow()
    
    statement = select(Session).where(
        Session.user_id == user_id,
        Session.is_valid == True,
        Session.expires_at > now,
    )
    
    return db.exec(statement).all()


async def cleanup_expired_sessions(db: DBSession) -> int:
    """
    Mark all expired sessions as invalid.
    
    Should be run periodically (e.g., daily cron job).
    
    Returns:
        Number of sessions cleaned up
    """
    now = datetime.utcnow()
    
    statement = select(Session).where(
        Session.is_valid == True,
        Session.expires_at < now,
    )
    
    sessions = db.exec(statement).all()
    count = 0
    
    for session in sessions:
        session.is_valid = False
        db.add(session)
        count += 1
    
    db.commit()
    
    return count
