"""
BioMind Nexus - Authentication Package

Production-grade authentication with:
- Hybrid JWT + server-side sessions
- bcrypt password hashing
- RBAC with deny-by-default
- Full audit trail integration
"""

from backend.auth.models import User, Session, Role
from backend.auth.dependencies import get_current_user, require_permission
from backend.auth.tokens import create_access_token, verify_access_token

__all__ = [
    "User",
    "Session",
    "Role",
    "get_current_user",
    "require_permission",
    "create_access_token",
    "verify_access_token",
]
