"""
BioMind Nexus - Hash Chain for Audit Integrity

Implements cryptographic hash chaining for tamper-evident audit logs.
Each audit event includes a hash of itself + the previous event's hash.

Verification:
- Any modification to an event breaks the chain
- Chain integrity can be verified by recomputing hashes
- Detects insertions, deletions, and modifications

Algorithm: SHA-256 (sufficient for local development)
"""

import hashlib
from typing import Optional
from datetime import date


def compute_event_hash(
    event_id: str,
    event_type: str,
    user_id: str,
    action: str,
    prev_hash: str,
) -> str:
    """
    Compute SHA-256 hash for an audit event.
    
    Hash includes:
    - Event ID
    - Event type
    - User ID
    - Action
    - Previous event hash (chain link)
    
    Args:
        event_id: Unique event identifier
        event_type: Event category
        user_id: Acting user
        action: Action performed
        prev_hash: Hash of previous event in chain
    
    Returns:
        Hex-encoded SHA-256 hash
    """
    content = f"{event_id}|{event_type}|{user_id}|{action}|{prev_hash}"
    return hashlib.sha256(content.encode()).hexdigest()


async def get_latest_hash(session, partition_date: date) -> str:
    """
    Get the hash of the most recent event for chain linking.
    
    Args:
        session: Cassandra session
        partition_date: Current partition date
    
    Returns:
        Latest event hash, or genesis hash if no events exist
    """
    result = session.execute("""
        SELECT hash FROM audit_events
        WHERE partition_date = %s
        LIMIT 1
    """, [partition_date])
    
    row = result.one()
    if row:
        return row.hash
    
    # Genesis hash for first event of the day
    return compute_genesis_hash(partition_date)


def compute_genesis_hash(partition_date: date) -> str:
    """
    Compute genesis hash for a new partition.
    
    The genesis hash includes the partition date to prevent
    cross-day chain attacks.
    
    Returns:
        Genesis hash for the partition
    """
    content = f"GENESIS|{partition_date.isoformat()}"
    return hashlib.sha256(content.encode()).hexdigest()


async def verify_chain(session, partition_date: date) -> bool:
    """
    Verify the integrity of the hash chain for a given date.
    
    Recomputes all hashes and verifies they match stored values.
    
    Args:
        session: Cassandra session
        partition_date: Date partition to verify
    
    Returns:
        True if chain is valid, False if tampering detected
    """
    # Fetch all events for the date (oldest first)
    result = session.execute("""
        SELECT event_id, event_type, user_id, action, hash, prev_hash
        FROM audit_events
        WHERE partition_date = %s
        ORDER BY event_id ASC
    """, [partition_date])
    
    events = list(result)
    if not events:
        return True  # No events to verify
    
    # Verify genesis
    expected_genesis = compute_genesis_hash(partition_date)
    if events[0].prev_hash != expected_genesis:
        return False
    
    # Verify each event in chain
    prev_hash = expected_genesis
    for event in events:
        expected_hash = compute_event_hash(
            event_id=str(event.event_id),
            event_type=event.event_type,
            user_id=event.user_id,
            action=event.action,
            prev_hash=prev_hash,
        )
        
        if event.hash != expected_hash:
            return False
        
        if event.prev_hash != prev_hash:
            return False
        
        prev_hash = event.hash
    
    return True


def export_chain_proof(session, partition_date: date) -> dict:
    """
    Export cryptographic proof for external verification.
    
    Returns a JSON-serializable structure containing:
    - Partition date
    - Genesis hash
    - Final hash
    - Event count
    - Merkle-style summary (future enhancement)
    
    This proof can be stored externally for non-repudiation.
    """
    # TODO: Implement proof export
    return {
        "partition_date": partition_date.isoformat(),
        "genesis_hash": compute_genesis_hash(partition_date),
        "final_hash": "",  # Would be computed
        "event_count": 0,
        "verified": False,
    }
