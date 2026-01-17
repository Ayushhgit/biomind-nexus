"""
Seed sample audit logs for testing Admin Dashboard
"""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Path to fallback log file
FALLBACK_LOG_FILE = Path("audit_fallback.jsonl")

def create_sample_logs():
    """Create sample audit log entries"""
    sample_logs = [
        {
            "event_id": str(uuid.uuid4()),
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "event_type": "USER_LOGIN",
            "user_id": "admin-user-123",
            "action": "login",
            "request_id": str(uuid.uuid4()),
            "details": json.dumps({
                "ip_address": "10.20.56.44",
                "user_agent": "Mozilla/5.0",
                "success": True
            })
        },
        {
            "event_id": str(uuid.uuid4()),
            "created_at": (datetime.utcnow() - timedelta(hours=1, minutes=30)).isoformat(),
            "event_type": "WORKFLOW_START",
            "user_id": "researcher-user-456",
            "action": "literature_agent",
            "request_id": str(uuid.uuid4()),
            "details": json.dumps({
                "query": "Can metformin be repurposed for breast cancer?",
                "step_index": 0
            })
        },
        {
            "event_id": str(uuid.uuid4()),
            "created_at": (datetime.utcnow() - timedelta(hours=1, minutes=25)).isoformat(),
            "event_type": "WORKFLOW_STEP",
            "user_id": "researcher-user-456",
            "action": "reasoning_agent",
            "request_id": str(uuid.uuid4()),
            "details": json.dumps({
                "candidates_found": 3,
                "step_index": 1
            })
        },
        {
            "event_id": str(uuid.uuid4()),
            "created_at": (datetime.utcnow() - timedelta(hours=1, minutes=20)).isoformat(),
            "event_type": "WORKFLOW_COMPLETE",
            "user_id": "researcher-user-456",
            "action": "orchestrator",
            "request_id": str(uuid.uuid4()),
            "details": json.dumps({
                "approved": True,
                "total_candidates": 3,
                "step_history": ["literature_agent", "reasoning_agent", "safety_agent"]
            })
        },
        {
            "event_id": str(uuid.uuid4()),
            "created_at": (datetime.utcnow() - timedelta(minutes=45)).isoformat(),
            "event_type": "USER_LOGOUT",
            "user_id": "admin-user-123",
            "action": "logout",
            "request_id": str(uuid.uuid4()),
            "details": json.dumps({
                "session_duration_seconds": 4500
            })
        },
        {
            "event_id": str(uuid.uuid4()),
            "created_at": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
            "event_type": "USER_LOGIN",
            "user_id": "admin-user-123",
            "action": "login",
            "request_id": str(uuid.uuid4()),
            "details": json.dumps({
                "ip_address": "10.20.56.44",
                "user_agent": "Mozilla/5.0",
                "success": True
            })
        }
    ]
    
    # Write to fallback file
    with open(FALLBACK_LOG_FILE, "w") as f:
        for log in sample_logs:
            f.write(json.dumps(log) + "\n")
    
    print(f"✅ Created {len(sample_logs)} sample audit log entries")
    print(f"📁 File: {FALLBACK_LOG_FILE.absolute()}")

if __name__ == "__main__":
    create_sample_logs()
