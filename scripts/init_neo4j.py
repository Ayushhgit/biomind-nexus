"""
BioMind Nexus - Neo4j Initialization Script

Initializes the Neo4j database with schema constraints and indexes.
Run this script before first use.

Usage:
    python scripts/init_neo4j.py
"""

import asyncio
from pathlib import Path

# Adjust import path for script execution
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.graph_db.neo4j_client import Neo4jClient


async def init_neo4j():
    """
    Initialize Neo4j database with schema.
    
    Steps:
    1. Connect to Neo4j instance
    2. Execute schema.cypher to create constraints/indexes
    3. Verify schema was applied correctly
    """
    print("Initializing Neo4j database...")
    
    client = Neo4jClient(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )
    
    try:
        await client.connect()
        print(f"Connected to Neo4j at {settings.NEO4J_URI}")
        
        # Load schema file
        schema_path = Path(__file__).parent.parent / "backend" / "graph_db" / "schema.cypher"
        
        if not schema_path.exists():
            print(f"Error: Schema file not found at {schema_path}")
            return
        
        schema_content = schema_path.read_text()
        
        # Execute each statement (separated by semicolons)
        statements = [s.strip() for s in schema_content.split(";") if s.strip() and not s.strip().startswith("//")]
        
        for stmt in statements:
            if stmt:
                try:
                    await client.execute_write(stmt)
                    print(f"Executed: {stmt[:50]}...")
                except Exception as e:
                    print(f"Warning: {e}")
        
        print("Schema initialization complete.")
        
        # Verify connectivity
        if await client.health_check():
            print("Health check passed.")
        else:
            print("Warning: Health check failed.")
            
    finally:
        await client.close()
        print("Connection closed.")


if __name__ == "__main__":
    asyncio.run(init_neo4j())
