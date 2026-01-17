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
import json
import os
from pathlib import Path

# =============================================================================
# Connection Management
# =============================================================================

_cassandra_client = None
FALLBACK_LOG_FILE = Path("audit_fallback.jsonl")


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
    
    # Prepare details
    details = {
        "input_hash": input_hash,
        "output_hash": output_hash,
        "step_index": step_index,
        **(metadata or {})
    }

    if client:
        try:
            await client.log_event(
                event_type=event_type,
                user_id=user_id,
                action=agent_name,
                request_id=request_id,
                details=details
            )
            return True
        except Exception as e:
            print(f"Audit logging error (Cassandra): {e}")
            # Fall through to specific file logging if needed, or just print
    
    # Fallback: Log to file if Cassandra is missing
    try:
        log_entry = {
            "event_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "action": agent_name,
            "request_id": request_id,
            "details": json.dumps(details)
        }
        with open(FALLBACK_LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        return True
    except Exception as e:
        print(f"Audit logging error (File Fallback): {e}")
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


async def get_all_audit_logs(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all audit logs (with fallback).
    """
    client = get_cassandra_client()
    logs = []

    if client:
        # Cassandra implementation (simplified query for now)
        pass # To be fully implemented when Cassandra is online
    
    # File fallback if no logs from Cassandra or Cassandra missing
    if not logs and FALLBACK_LOG_FILE.exists():
        try:
            with open(FALLBACK_LOG_FILE, "r") as f:
                lines = f.readlines()
                # Read reverse order (newest first)
                for line in reversed(lines):
                    try:
                        entry = json.loads(line)
                        
                        # Apply filters
                        if event_type and entry.get("event_type") != event_type:
                            continue
                        if user_id and entry.get("user_id") != user_id:
                            continue
                            
                        # Parse created_at to datetime object if needed, or keep string
                        # For consistency with DB, let's keep it compatible
                        
                        logs.append(entry)
                        
                        if len(logs) >= limit + offset:
                            break
                    except:
                        continue
                        
            # Apply offset/limit
            logs = logs[offset:offset+limit]
            
        except Exception as e:
            print(f"Error reading fallback logs: {e}")

    return logs


async def get_workflow_history(
    request_id: str
) -> List[Dict[str, Any]]:
    """
    Retrieve audit history for a workflow.
    """
    client = get_cassandra_client()
    
    # Fallback
    history = []
    if FALLBACK_LOG_FILE.exists():
        try:
            with open(FALLBACK_LOG_FILE, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("request_id") == request_id:
                        history.append(entry)
        except: pass
        
    return history
