"""
BioMind Nexus - Role-Based Access Control (RBAC)

Fine-grained permission control based on user roles.
Policies are defined in policies.yaml and enforced at the route level.

Security:
- Deny-by-default: All actions require explicit permission
- Role hierarchy is NOT inherited (explicit grants only)
- All authorization decisions are logged
"""

from enum import Enum
from typing import Set, Dict
from functools import wraps
from pathlib import Path

import yaml
from fastapi import HTTPException, status

from backend.gateway.auth import AuthenticatedUser


class Role(str, Enum):
    """Defined user roles in the system."""
    ADMIN = "admin"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


class Permission(str, Enum):
    """Granular permissions for system actions."""
    # Agent interactions
    QUERY_AGENTS = "query:agents"
    INVOKE_LITERATURE_AGENT = "invoke:literature_agent"
    INVOKE_REASONING_AGENT = "invoke:reasoning_agent"
    INVOKE_SAFETY_AGENT = "invoke:safety_agent"
    
    # Data access
    READ_GRAPH = "read:graph"
    WRITE_GRAPH = "write:graph"
    READ_AUDIT = "read:audit"
    EXPORT_AUDIT = "export:audit"
    
    # Dossier
    GENERATE_DOSSIER = "generate:dossier"
    EXPORT_DOSSIER = "export:dossier"


class RBACPolicy:
    """
    Manages role-to-permission mappings loaded from policies.yaml.
    
    Thread-safe singleton pattern for policy access.
    """
    
    _instance = None
    _policies: Dict[str, Set[str]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_policies()
        return cls._instance
    
    def _load_policies(self):
        """Load policies from YAML configuration file."""
        policy_path = Path(__file__).parent / "policies.yaml"
        
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
            True if permitted, False otherwise
        """
        role_perms = self._policies.get(role, set())
        return permission.value in role_perms


def require_permission(permission: Permission):
    """
    Decorator to enforce permission requirements on routes.
    
    Usage:
        @app.get("/protected")
        @require_permission(Permission.READ_GRAPH)
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (injected by Depends)
            user: AuthenticatedUser = kwargs.get("user")
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            policy = RBACPolicy()
            if not policy.has_permission(user.role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
