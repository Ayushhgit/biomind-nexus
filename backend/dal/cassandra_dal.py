"""
Cassandra Data Access Layer

Provides structured access to audit logs.
Returns domain objects, not raw database records.

Golden Rule: Agents never call this directly.
             Orchestrator logs events after workflow completion.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


# =============================================================================
# Connection Management
# =============================================================================

_cassandra_client = None


def set_cassandra_client(client) -> None:
    """Set the global Cassandra client (called at app startup)."""
    global _cassandra_client
    _cassandra_client = client


def get_cassandra_client():
    """Get the current Cassandra client."""
    return _cassandra_client


# =============================================================================
# Audit Logging Functions
# =============================================================================

async def log_workflow_event(
    request_id: str,
    user_id: str,
    event_type: str,
    agent_name: str,
    input_hash: str,
    output_hash: str,
    step_index: int,
    metadata: Dict[str, Any] = None
) -> bool:
    """
    Log a workflow event to the audit trail.
    
    Called by the orchestrator AFTER each agent completes.
    Agents do NOT have access to this function.
    """
    client = get_cassandra_client()
    if not client:
        # Graceful degradation: just print to console
        print(f"AUDIT: [{event_type}] {agent_name} for request {request_id}")
        return True
    
    try:
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Insert into Cassandra
        await client.execute_async(
            """
            INSERT INTO workflow_events (
                event_id, request_id, user_id, event_type, 
                agent_name, input_hash, output_hash, 
                step_index, timestamp, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id, request_id, user_id, event_type,
                agent_name, input_hash, output_hash,
                step_index, timestamp, metadata or {}
            )
        )
        return True
    except Exception as e:
        print(f"Audit logging error: {e}")
        return False


async def log_workflow_complete(
    request_id: str,
    user_id: str,
    approved: bool,
    step_history: List[str],
    total_candidates: int
) -> bool:
    """
    Log workflow completion event.
    """
    return await log_workflow_event(
        request_id=request_id,
        user_id=user_id,
        event_type="WORKFLOW_COMPLETE",
        agent_name="orchestrator",
        input_hash="",
        output_hash="",
        step_index=len(step_history),
        metadata={
            "approved": approved,
            "step_history": step_history,
            "total_candidates": total_candidates
        }
    )


async def get_workflow_history(
    request_id: str
) -> List[Dict[str, Any]]:
    """
    Retrieve audit history for a workflow.
    
    Called by admin/auditor roles, NOT agents.
    """
    client = get_cassandra_client()
    if not client:
        return []
    
    try:
        results = await client.execute_async(
            """
            SELECT event_id, event_type, agent_name, timestamp, metadata
            FROM workflow_events
            WHERE request_id = ?
            ORDER BY timestamp
            """,
            (request_id,)
        )
        
        return [
            {
                "event_id": row.event_id,
                "event_type": row.event_type,
                "agent_name": row.agent_name,
                "timestamp": row.timestamp,
                "metadata": row.metadata
            }
            for row in results
        ]
    except Exception as e:
        print(f"Audit query error: {e}")
        return []


async def get_user_workflow_history(
    user_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get recent workflows for a user.
    """
    client = get_cassandra_client()
    if not client:
        return []
    
    try:
        results = await client.execute_async(
            """
            SELECT request_id, event_type, timestamp, metadata
            FROM workflow_events
            WHERE user_id = ?
            AND event_type = 'WORKFLOW_COMPLETE'
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit)
        )
        
        return [
            {
                "request_id": row.request_id,
                "timestamp": row.timestamp,
                "approved": row.metadata.get("approved", False),
                "total_candidates": row.metadata.get("total_candidates", 0)
            }
            for row in results
        ]
    except Exception as e:
        print(f"Audit query error: {e}")
        return []
