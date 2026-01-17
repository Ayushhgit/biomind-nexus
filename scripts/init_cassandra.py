"""
BioMind Nexus - Cassandra Initialization Script

Initializes the Cassandra keyspace and tables for audit logging.
Run this script before first use.

Usage:
    python scripts/init_cassandra.py
"""

import asyncio
from pathlib import Path

# Adjust import path for script execution
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.audit.cassandra_client import CassandraAuditClient


async def init_cassandra():
    """
    Initialize Cassandra keyspace and tables.
    
    Creates:
    - biomind_audit keyspace
    - audit_events table
    """
    print("Initializing Cassandra database...")
    
    client = CassandraAuditClient(
        hosts=settings.CASSANDRA_HOSTS,
        keyspace=settings.CASSANDRA_KEYSPACE,
    )
    
    try:
        await client.connect()
        print(f"Connected to Cassandra at {settings.CASSANDRA_HOSTS}")
        print(f"Keyspace '{settings.CASSANDRA_KEYSPACE}' initialized.")
        
        # Verify connectivity
        if await client.health_check():
            print("Health check passed.")
        else:
            print("Warning: Health check failed.")
            
    finally:
        await client.close()
        print("Connection closed.")


if __name__ == "__main__":
    asyncio.run(init_cassandra())
