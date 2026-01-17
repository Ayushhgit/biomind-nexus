"""
BioMind Nexus - Demo Data Seeding Script

Seeds the databases with sample data for local development and testing.
Run after init_neo4j.py and init_cassandra.py.

Usage:
    python scripts/seed_demo_data.py
"""

import asyncio
from pathlib import Path

# Adjust import path for script execution
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.graph_db.neo4j_client import Neo4jClient


# Sample biomedical entities for demo
DEMO_GENES = [
    {"id": "BRCA1", "symbol": "BRCA1", "name": "BRCA1 DNA repair associated"},
    {"id": "TP53", "symbol": "TP53", "name": "Tumor protein P53"},
    {"id": "EGFR", "symbol": "EGFR", "name": "Epidermal growth factor receptor"},
]

DEMO_DISEASES = [
    {"id": "DOID:1612", "name": "Breast cancer"},
    {"id": "DOID:1324", "name": "Lung cancer"},
    {"id": "DOID:9256", "name": "Colorectal cancer"},
]

DEMO_DRUGS = [
    {"id": "DB00072", "name": "Trastuzumab"},
    {"id": "DB00530", "name": "Erlotinib"},
]


async def seed_demo_data():
    """
    Seed Neo4j with demo biomedical data.
    """
    print("Seeding demo data...")
    
    client = Neo4jClient(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )
    
    try:
        await client.connect()
        print("Connected to Neo4j.")
        
        # Seed genes
        for gene in DEMO_GENES:
            await client.execute_write("""
                MERGE (g:Gene {id: $id})
                SET g.symbol = $symbol, g.name = $name
            """, gene)
            print(f"Created gene: {gene['symbol']}")
        
        # Seed diseases
        for disease in DEMO_DISEASES:
            await client.execute_write("""
                MERGE (d:Disease {id: $id})
                SET d.name = $name
            """, disease)
            print(f"Created disease: {disease['name']}")
        
        # Seed drugs
        for drug in DEMO_DRUGS:
            await client.execute_write("""
                MERGE (dr:Drug {id: $id})
                SET dr.name = $name
            """, drug)
            print(f"Created drug: {drug['name']}")
        
        # Create sample relationships
        await client.execute_write("""
            MATCH (g:Gene {id: 'BRCA1'}), (d:Disease {id: 'DOID:1612'})
            MERGE (g)-[:ASSOCIATED_WITH {score: 0.95, source: 'demo'}]->(d)
        """)
        print("Created BRCA1 -> Breast cancer association")
        
        await client.execute_write("""
            MATCH (dr:Drug {id: 'DB00530'}), (g:Gene {id: 'EGFR'})
            MERGE (dr)-[:TARGETS {action: 'inhibitor', score: 0.9}]->(g)
        """)
        print("Created Erlotinib -> EGFR target")
        
        print("Demo data seeding complete.")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
