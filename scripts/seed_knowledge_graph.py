"""
BioMind Nexus - Knowledge Graph Seed Data

Seeds the Neo4j database with sample biomedical data for drug repurposing.
Includes drugs, genes, diseases, and their relationships.

Usage:
    python scripts/seed_knowledge_graph.py

Prerequisites:
    - Neo4j running (docker-compose up -d)
    - NEO4J_PASSWORD set in .env
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.graph_db.neo4j_client import Neo4jClient


# =============================================================================
# Sample Biomedical Data
# =============================================================================

DRUGS = [
    {"id": "DB00331", "name": "Metformin", "drugbank_id": "DB00331", 
     "description": "Biguanide antidiabetic agent used for type 2 diabetes"},
    {"id": "DB00945", "name": "Aspirin", "drugbank_id": "DB00945",
     "description": "NSAID with antiplatelet and anti-inflammatory properties"},
    {"id": "DB00641", "name": "Simvastatin", "drugbank_id": "DB00641",
     "description": "Statin medication for lowering cholesterol"},
    {"id": "DB01050", "name": "Ibuprofen", "drugbank_id": "DB01050",
     "description": "NSAID for pain relief and inflammation"},
    {"id": "DB00959", "name": "Methylprednisolone", "drugbank_id": "DB00959",
     "description": "Corticosteroid with anti-inflammatory effects"},
    {"id": "DB00563", "name": "Methotrexate", "drugbank_id": "DB00563",
     "description": "Antimetabolite used in cancer and autoimmune diseases"},
    {"id": "DB00795", "name": "Sulfasalazine", "drugbank_id": "DB00795",
     "description": "Anti-inflammatory for rheumatoid arthritis and IBD"},
    {"id": "DB01076", "name": "Atorvastatin", "drugbank_id": "DB01076",
     "description": "Statin for cholesterol and cardiovascular disease"},
]

GENES = [
    {"id": "HGNC:795", "symbol": "AMPK", "name": "AMP-activated protein kinase",
     "description": "Master regulator of cellular energy homeostasis"},
    {"id": "HGNC:9236", "symbol": "PPARG", "name": "Peroxisome proliferator-activated receptor gamma",
     "description": "Nuclear receptor regulating fatty acid storage and glucose metabolism"},
    {"id": "HGNC:2367", "symbol": "COX2", "name": "Cyclooxygenase-2",
     "description": "Enzyme in prostaglandin synthesis, inflammation mediator"},
    {"id": "HGNC:4556", "symbol": "HMGCR", "name": "HMG-CoA reductase",
     "description": "Rate-limiting enzyme in cholesterol synthesis"},
    {"id": "HGNC:11892", "symbol": "TNF", "name": "Tumor necrosis factor",
     "description": "Pro-inflammatory cytokine involved in systemic inflammation"},
    {"id": "HGNC:6018", "symbol": "IL6", "name": "Interleukin 6",
     "description": "Cytokine with pro-inflammatory and anti-inflammatory roles"},
    {"id": "HGNC:5972", "symbol": "IL1B", "name": "Interleukin 1 beta",
     "description": "Pro-inflammatory cytokine mediator"},
    {"id": "HGNC:7897", "symbol": "NFKB1", "name": "Nuclear factor kappa B subunit 1",
     "description": "Transcription factor regulating immune response"},
    {"id": "HGNC:6407", "symbol": "LDLR", "name": "Low density lipoprotein receptor",
     "description": "Receptor mediating LDL cholesterol uptake"},
    {"id": "HGNC:6871", "symbol": "MTOR", "name": "Mechanistic target of rapamycin",
     "description": "Serine/threonine kinase regulating cell growth"},
]

DISEASES = [
    {"id": "DOID:9351", "name": "Diabetes mellitus type 2", "doid": "DOID:9351",
     "description": "Metabolic disorder characterized by high blood sugar"},
    {"id": "DOID:10763", "name": "Hypertension", "doid": "DOID:10763",
     "description": "Chronic elevation of blood pressure"},
    {"id": "DOID:114", "name": "Heart disease", "doid": "DOID:114",
     "description": "Class of diseases affecting the heart"},
    {"id": "DOID:10652", "name": "Alzheimer's disease", "doid": "DOID:10652",
     "description": "Progressive neurodegenerative disease"},
    {"id": "DOID:7148", "name": "Rheumatoid arthritis", "doid": "DOID:7148",
     "description": "Chronic autoimmune inflammatory disorder"},
    {"id": "DOID:8398", "name": "Osteoarthritis", "doid": "DOID:8398",
     "description": "Degenerative joint disease"},
    {"id": "DOID:3083", "name": "COPD", "doid": "DOID:3083",
     "description": "Chronic obstructive pulmonary disease"},
    {"id": "DOID:9352", "name": "Diabetes mellitus type 1", "doid": "DOID:9352",
     "description": "Autoimmune diabetes with insulin deficiency"},
    {"id": "DOID:10283", "name": "Prostate cancer", "doid": "DOID:10283",
     "description": "Cancer of the prostate gland"},
    {"id": "DOID:1612", "name": "Breast cancer", "doid": "DOID:1612",
     "description": "Cancer originating from breast tissue"},
]

PATHWAYS = [
    {"id": "KEGG:hsa04910", "name": "Insulin signaling pathway", "source": "KEGG"},
    {"id": "KEGG:hsa04151", "name": "PI3K-Akt signaling pathway", "source": "KEGG"},
    {"id": "KEGG:hsa04668", "name": "TNF signaling pathway", "source": "KEGG"},
    {"id": "KEGG:hsa04064", "name": "NF-kappa B signaling pathway", "source": "KEGG"},
    {"id": "KEGG:hsa00900", "name": "Terpenoid backbone biosynthesis", "source": "KEGG"},
    {"id": "GO:0006954", "name": "Inflammatory response", "source": "GO"},
    {"id": "GO:0006955", "name": "Immune response", "source": "GO"},
]

# Relationships: (source, relationship, target, properties)
DRUG_TARGETS = [
    ("DB00331", "TARGETS", "HGNC:795", {"action": "activator", "score": 0.95}),   # Metformin -> AMPK
    ("DB00331", "TARGETS", "HGNC:6871", {"action": "inhibitor", "score": 0.7}),   # Metformin -> MTOR
    ("DB00945", "TARGETS", "HGNC:2367", {"action": "inhibitor", "score": 0.99}),  # Aspirin -> COX2
    ("DB00641", "TARGETS", "HGNC:4556", {"action": "inhibitor", "score": 0.98}),  # Simvastatin -> HMGCR
    ("DB01050", "TARGETS", "HGNC:2367", {"action": "inhibitor", "score": 0.95}),  # Ibuprofen -> COX2
    ("DB00959", "TARGETS", "HGNC:7897", {"action": "inhibitor", "score": 0.85}),  # Methylpred -> NFKB1
    ("DB00563", "TARGETS", "HGNC:6871", {"action": "inhibitor", "score": 0.8}),   # Methotrexate -> MTOR
    ("DB01076", "TARGETS", "HGNC:4556", {"action": "inhibitor", "score": 0.97}),  # Atorvastatin -> HMGCR
]

GENE_DISEASE = [
    ("HGNC:795", "ASSOCIATED_WITH", "DOID:9351", {"score": 0.9, "evidence": "clinical"}),   # AMPK -> Diabetes
    ("HGNC:9236", "ASSOCIATED_WITH", "DOID:9351", {"score": 0.85, "evidence": "clinical"}), # PPARG -> Diabetes
    ("HGNC:2367", "ASSOCIATED_WITH", "DOID:7148", {"score": 0.88, "evidence": "clinical"}), # COX2 -> RA
    ("HGNC:4556", "ASSOCIATED_WITH", "DOID:114", {"score": 0.92, "evidence": "clinical"}),  # HMGCR -> Heart disease
    ("HGNC:11892", "ASSOCIATED_WITH", "DOID:7148", {"score": 0.95, "evidence": "clinical"}),# TNF -> RA
    ("HGNC:6018", "ASSOCIATED_WITH", "DOID:7148", {"score": 0.87, "evidence": "clinical"}), # IL6 -> RA
    ("HGNC:6018", "ASSOCIATED_WITH", "DOID:10652", {"score": 0.7, "evidence": "research"}), # IL6 -> Alzheimer's
    ("HGNC:5972", "ASSOCIATED_WITH", "DOID:10652", {"score": 0.75, "evidence": "research"}),# IL1B -> Alzheimer's
    ("HGNC:7897", "ASSOCIATED_WITH", "DOID:7148", {"score": 0.85, "evidence": "clinical"}), # NFKB1 -> RA
    ("HGNC:6407", "ASSOCIATED_WITH", "DOID:114", {"score": 0.9, "evidence": "clinical"}),   # LDLR -> Heart disease
    ("HGNC:6871", "ASSOCIATED_WITH", "DOID:10283", {"score": 0.8, "evidence": "research"}), # MTOR -> Prostate cancer
]

DRUG_DISEASE = [
    ("DB00331", "TREATS", "DOID:9351", {"phase": "approved", "approval_status": "FDA"}),
    ("DB00641", "TREATS", "DOID:114", {"phase": "approved", "approval_status": "FDA"}),
    ("DB00795", "TREATS", "DOID:7148", {"phase": "approved", "approval_status": "FDA"}),
    ("DB01076", "TREATS", "DOID:114", {"phase": "approved", "approval_status": "FDA"}),
]

GENE_PATHWAY = [
    ("HGNC:795", "PARTICIPATES_IN", "KEGG:hsa04910"),   # AMPK -> Insulin signaling
    ("HGNC:795", "PARTICIPATES_IN", "KEGG:hsa04151"),   # AMPK -> PI3K-Akt
    ("HGNC:9236", "PARTICIPATES_IN", "KEGG:hsa04910"),  # PPARG -> Insulin signaling
    ("HGNC:2367", "PARTICIPATES_IN", "GO:0006954"),     # COX2 -> Inflammatory response
    ("HGNC:11892", "PARTICIPATES_IN", "KEGG:hsa04668"), # TNF -> TNF signaling
    ("HGNC:11892", "PARTICIPATES_IN", "GO:0006954"),    # TNF -> Inflammatory response
    ("HGNC:6018", "PARTICIPATES_IN", "GO:0006955"),     # IL6 -> Immune response
    ("HGNC:7897", "PARTICIPATES_IN", "KEGG:hsa04064"),  # NFKB1 -> NF-kappa B signaling
    ("HGNC:6871", "PARTICIPATES_IN", "KEGG:hsa04151"),  # MTOR -> PI3K-Akt
]

GENE_INTERACTIONS = [
    ("HGNC:795", "REGULATES", "HGNC:6871", {"direction": "inhibits"}),   # AMPK inhibits MTOR
    ("HGNC:795", "REGULATES", "HGNC:9236", {"direction": "activates"}),  # AMPK activates PPARG
    ("HGNC:11892", "REGULATES", "HGNC:7897", {"direction": "activates"}),# TNF activates NFKB1
    ("HGNC:7897", "REGULATES", "HGNC:6018", {"direction": "activates"}), # NFKB1 activates IL6
    ("HGNC:7897", "REGULATES", "HGNC:2367", {"direction": "activates"}), # NFKB1 activates COX2
    ("HGNC:5972", "REGULATES", "HGNC:7897", {"direction": "activates"}), # IL1B activates NFKB1
]


# =============================================================================
# Seed Functions
# =============================================================================

async def create_nodes(client: Neo4jClient):
    """Create all entity nodes."""
    print("\n📦 Creating nodes...")
    
    # Drugs
    for drug in DRUGS:
        await client.execute_write("""
            MERGE (d:Drug {id: $id})
            SET d.name = $name, d.drugbank_id = $drugbank_id, d.description = $description
        """, drug)
    print(f"  ✓ Created {len(DRUGS)} Drug nodes")
    
    # Genes
    for gene in GENES:
        await client.execute_write("""
            MERGE (g:Gene {id: $id})
            SET g.symbol = $symbol, g.name = $name, g.description = $description
        """, gene)
    print(f"  ✓ Created {len(GENES)} Gene nodes")
    
    # Diseases
    for disease in DISEASES:
        await client.execute_write("""
            MERGE (d:Disease {id: $id})
            SET d.name = $name, d.doid = $doid, d.description = $description
        """, disease)
    print(f"  ✓ Created {len(DISEASES)} Disease nodes")
    
    # Pathways
    for pathway in PATHWAYS:
        await client.execute_write("""
            MERGE (p:Pathway {id: $id})
            SET p.name = $name, p.source = $source
        """, pathway)
    print(f"  ✓ Created {len(PATHWAYS)} Pathway nodes")


async def create_relationships(client: Neo4jClient):
    """Create all relationships."""
    print("\n🔗 Creating relationships...")
    
    # Drug-Gene (TARGETS)
    for source, rel_type, target, props in DRUG_TARGETS:
        await client.execute_write(f"""
            MATCH (d:Drug {{id: $source}}), (g:Gene {{id: $target}})
            MERGE (d)-[r:{rel_type}]->(g)
            SET r.action = $action, r.score = $score
        """, {"source": source, "target": target, **props})
    print(f"  ✓ Created {len(DRUG_TARGETS)} Drug-TARGETS-Gene relationships")
    
    # Gene-Disease (ASSOCIATED_WITH)
    for source, rel_type, target, props in GENE_DISEASE:
        await client.execute_write(f"""
            MATCH (g:Gene {{id: $source}}), (d:Disease {{id: $target}})
            MERGE (g)-[r:{rel_type}]->(d)
            SET r.score = $score, r.evidence = $evidence
        """, {"source": source, "target": target, **props})
    print(f"  ✓ Created {len(GENE_DISEASE)} Gene-ASSOCIATED_WITH-Disease relationships")
    
    # Drug-Disease (TREATS)
    for source, rel_type, target, props in DRUG_DISEASE:
        await client.execute_write(f"""
            MATCH (dr:Drug {{id: $source}}), (d:Disease {{id: $target}})
            MERGE (dr)-[r:{rel_type}]->(d)
            SET r.phase = $phase, r.approval_status = $approval_status
        """, {"source": source, "target": target, **props})
    print(f"  ✓ Created {len(DRUG_DISEASE)} Drug-TREATS-Disease relationships")
    
    # Gene-Pathway (PARTICIPATES_IN)
    for source, rel_type, target in GENE_PATHWAY:
        await client.execute_write(f"""
            MATCH (g:Gene {{id: $source}}), (p:Pathway {{id: $target}})
            MERGE (g)-[r:{rel_type}]->(p)
        """, {"source": source, "target": target})
    print(f"  ✓ Created {len(GENE_PATHWAY)} Gene-PARTICIPATES_IN-Pathway relationships")
    
    # Gene-Gene (REGULATES)
    for source, rel_type, target, props in GENE_INTERACTIONS:
        await client.execute_write(f"""
            MATCH (g1:Gene {{id: $source}}), (g2:Gene {{id: $target}})
            MERGE (g1)-[r:{rel_type}]->(g2)
            SET r.direction = $direction
        """, {"source": source, "target": target, **props})
    print(f"  ✓ Created {len(GENE_INTERACTIONS)} Gene-REGULATES-Gene relationships")


async def verify_data(client: Neo4jClient):
    """Verify seeded data."""
    print("\n📊 Verifying data...")
    
    counts = await client.execute_read("""
        MATCH (d:Drug) WITH count(d) as drugs
        MATCH (g:Gene) WITH drugs, count(g) as genes
        MATCH (dis:Disease) WITH drugs, genes, count(dis) as diseases
        MATCH (p:Pathway) WITH drugs, genes, diseases, count(p) as pathways
        MATCH ()-[r]->() WITH drugs, genes, diseases, pathways, count(r) as relationships
        RETURN drugs, genes, diseases, pathways, relationships
    """)
    
    if counts:
        c = counts[0]
        print(f"  • Drugs: {c['drugs']}")
        print(f"  • Genes: {c['genes']}")
        print(f"  • Diseases: {c['diseases']}")
        print(f"  • Pathways: {c['pathways']}")
        print(f"  • Relationships: {c['relationships']}")


async def seed_database():
    """Main seed function."""
    print("=" * 60)
    print("BioMind Nexus - Knowledge Graph Seeder")
    print("=" * 60)
    
    client = Neo4jClient(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD or "biomind2024",
    )
    
    try:
        await client.connect()
        print(f"✓ Connected to Neo4j at {settings.NEO4J_URI}")
        
        await create_nodes(client)
        await create_relationships(client)
        await verify_data(client)
        
        print("\n" + "=" * 60)
        print("✅ Knowledge graph seeding complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Neo4j is running:")
        print("  docker-compose up -d")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
