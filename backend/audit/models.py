"""
BioMind Nexus - Audit Models

Pydantic models for audit events and related structures.
These models ensure type safety and validation for audit operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Categories of auditable events."""
    AUTH = "auth"           # Authentication events
    QUERY = "query"         # Agent queries
    ACTION = "action"       # System actions
    ERROR = "error"         # Error events
    ADMIN = "admin"         # Administrative actions
    EXPORT = "export"       # Data export events


class AuditEvent(BaseModel):
    """
    Represents a single audit log entry.
    
    All fields are immutable after creation.
    """
    event_id: str = Field(..., description="UUID for the event")
    event_type: EventType
    user_id: str
    request_id: Optional[str] = None
    action: str = Field(..., description="Action performed")
    resource: Optional[str] = Field(None, description="Target resource")
    details: Dict[str, Any] = Field(default_factory=dict)
    hash: str = Field(..., description="SHA-256 hash of event")
    prev_hash: str = Field(..., description="Hash of previous event")
    created_at: datetime


class AuditQuery(BaseModel):
    """Parameters for querying audit logs."""
    start_date: datetime
    end_date: datetime
    user_id: Optional[str] = None
    event_type: Optional[EventType] = None
    action: Optional[str] = None
    limit: int = Field(default=100, le=1000)


class ChainVerificationResult(BaseModel):
    """Result of audit chain verification."""
    partition_date: str
    is_valid: bool
    event_count: int
    first_event_id: Optional[str] = None
    last_event_id: Optional[str] = None
    genesis_hash: str
    final_hash: Optional[str] = None
    broken_at: Optional[str] = Field(
        None, 
        description="Event ID where chain broke, if invalid"
    )


class AuditExport(BaseModel):
    """Structure for exported audit data."""
    export_id: str
    exported_by: str
    export_timestamp: datetime
    date_range: Dict[str, str]
    event_count: int
    events: List[AuditEvent]
    chain_proof: Dict[str, Any]
