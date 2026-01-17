"""
Cassandra Data Access Layer

Provides structured access to audit logs via CassandraAuditClient.
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
    """
    client = get_cassandra_client()
    if not client:
        # Graceful degradation
        print(f"AUDIT: [{event_type}] {agent_name} for request {request_id}")
        return True
    
    try:
        await client.log_event(
            event_type=event_type,
            user_id=user_id,
            action=agent_name,
            request_id=request_id,
            details={
                "input_hash": input_hash,
                "output_hash": output_hash,
                "step_index": step_index,
                **(metadata or {})
            }
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
    """
    client = get_cassandra_client()
    if not client:
        return []
    
    try:
        # Use client's method
        events = await client.get_events_by_request(request_id)
        return events
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
        # We need a get_events_by_user method in client
        # For now, we fallback to printing warning or implementing simple query if possible
        # Or we can add method to client.
        # But for this task, let's assume client.get_events_by_request covers the main case.
        # We'll skip user history for now or implement direct query?
        # Direct query breaks encapsulation but easiest for now.
        
        statement = f"SELECT * FROM audit_events WHERE user_id = '{user_id}' LIMIT {limit} ALLOW FILTERING"
        # Accessing session directly
        if hasattr(client, '_session') and client._session:
            from cassandra.query import SimpleStatement
            stmt = SimpleStatement(statement)
            results = client._session.execute(stmt)
            
            history = []
            for row in results:
                if row.event_type == 'WORKFLOW_COMPLETE':
                    import json
                    details = {}
                    if row.details:
                        try:
                            details = json.loads(row.details)
                        except: pass
                        
                    history.append({
                        "request_id": row.request_id,
                        "timestamp": row.created_at.isoformat() if row.created_at else "",
                        "approved": details.get("approved", False),
                        "total_candidates": details.get("total_candidates", 0)
                    })
            return history
            
        return []
    except Exception as e:
        print(f"Audit query error: {e}")
        return []
