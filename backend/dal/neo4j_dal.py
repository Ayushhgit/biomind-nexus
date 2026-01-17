"""
Neo4j Data Access Layer

Provides structured access to the biomedical knowledge graph.
Returns domain objects, not raw database records.

Golden Rule: Agents never call this directly.
             Orchestrator loads data into AgentState before agents run.
"""

from typing import List, Dict, Any, Optional, TypedDict
from datetime import datetime
from backend.graph_db.neo4j_client import Neo4jClient
from backend.agents.schemas import (
    BiomedicalEntity,
    EntityType,
    BiologicalEdge,
    RelationType,
    ExtractionMethod,
)


# =============================================================================
# Connection Management
# =============================================================================

_neo4j_client: Optional[Neo4jClient] = None


def set_neo4j_client(client: Neo4jClient) -> None:
    """Set the global Neo4j client (called at app startup)."""
    global _neo4j_client
    _neo4j_client = client


def get_neo4j_client() -> Optional[Neo4jClient]:
    """Get the current Neo4j client."""
    return _neo4j_client


# =============================================================================
# Domain Query Functions (READ)
# =============================================================================

async def get_drug_targets(drug_name: str) -> List[BiomedicalEntity]:
    """
    Get known targets (genes/proteins) for a drug.
    """
    client = get_neo4j_client()
    if not client:
        return []
    
    query = """
    MATCH (d:Drug)-[r:TARGETS|INHIBITS|ACTIVATES|MODULATES]->(t)
    WHERE toLower(d.name) CONTAINS toLower($drug)
    RETURN t.id AS id, t.name AS name, labels(t) AS labels, 
           type(r) AS relation, r.confidence AS confidence
    LIMIT 20
    """
    
    try:
        results = await client.execute_read(query, {"drug": drug_name})
        
        entities = []
        for row in results:
            entity_type = _infer_entity_type(row.get("labels", []))
            entities.append(BiomedicalEntity(
                id=row.get("id", f"neo4j:{row.get('name', '').lower()}"),
                name=row.get("name", ""),
                entity_type=entity_type,
                extraction_method=ExtractionMethod.MANUAL,
                extraction_confidence=row.get("confidence", 0.8),
                metadata={"source": "neo4j", "relation": row.get("relation")}
            ))
        
        return entities
    except Exception as e:
        print(f"Neo4j query error: {e}")
        return []


async def get_disease_genes(disease_name: str) -> List[BiomedicalEntity]:
    """
    Get genes associated with a disease.
    """
    client = get_neo4j_client()
    if not client:
        return []
    
    query = """
    MATCH (g:Gene)-[r:ASSOCIATED_WITH|CAUSES|REGULATES]->(d:Disease)
    WHERE toLower(d.name) CONTAINS toLower($disease)
    RETURN g.id AS id, g.name AS name, type(r) AS relation,
           r.confidence AS confidence
    LIMIT 20
    """
    
    try:
        results = await client.execute_read(query, {"disease": disease_name})
        
        entities = []
        for row in results:
            entities.append(BiomedicalEntity(
                id=row.get("id", f"gene:{row.get('name', '').upper()}"),
                name=row.get("name", "").upper(),
                entity_type=EntityType.GENE,
                extraction_method=ExtractionMethod.MANUAL,
                extraction_confidence=row.get("confidence", 0.8),
                metadata={"source": "neo4j", "relation": row.get("relation")}
            ))
        
        return entities
    except Exception as e:
        print(f"Neo4j query error: {e}")
        return []


async def get_pathway_edges(
    source_entity: str,
    target_entity: str = None
) -> List[BiologicalEdge]:
    """
    Get edges connecting entities via pathways.
    """
    client = get_neo4j_client()
    if not client:
        return []
    
    if target_entity:
        query = """
        MATCH path = shortestPath(
            (s)-[*1..4]-(t)
        )
        WHERE toLower(s.name) CONTAINS toLower($source)
          AND toLower(t.name) CONTAINS toLower($target)
        UNWIND relationships(path) AS rel
        RETURN startNode(rel).name AS source_name,
               type(rel) AS relation,
               endNode(rel).name AS target_name,
               rel.confidence AS confidence
        LIMIT 50
        """
        params = {"source": source_entity, "target": target_entity}
    else:
        query = """
        MATCH (s)-[r]->(t)
        WHERE toLower(s.name) CONTAINS toLower($source)
        RETURN s.name AS source_name,
               type(r) AS relation,
               t.name AS target_name,
               r.confidence AS confidence
        LIMIT 30
        """
        params = {"source": source_entity}
    
    try:
        results = await client.execute_read(query, params)
        
        edges = []
        for row in results:
            relation = _map_relation_type(row.get("relation", ""))
            edges.append(BiologicalEdge(
                source_entity=row.get("source_name", ""),
                target_entity=row.get("target_name", ""),
                relation=relation,
                confidence=row.get("confidence", 0.7),
                evidence_count=1,
                pmid_support=[]
            ))
        
        return edges
    except Exception as e:
        print(f"Neo4j query error: {e}")
        return []


async def get_entity_neighbors(
    entity_name: str,
    max_depth: int = 2
) -> List[BiomedicalEntity]:
    """
    Get neighboring entities within N hops.
    """
    client = get_neo4j_client()
    if not client:
        return []
    
    query = f"""
    MATCH (s)-[*1..{max_depth}]-(n)
    WHERE toLower(s.name) CONTAINS toLower($entity)
    RETURN DISTINCT n.id AS id, n.name AS name, labels(n) AS labels
    LIMIT 50
    """
    
    try:
        results = await client.execute_read(query, {"entity": entity_name})
        
        entities = []
        for row in results:
            entity_type = _infer_entity_type(row.get("labels", []))
            entities.append(BiomedicalEntity(
                id=row.get("id", f"neo4j:{row.get('name', '').lower()}"),
                name=row.get("name", ""),
                entity_type=entity_type,
                extraction_method=ExtractionMethod.MANUAL,
                extraction_confidence=0.8,
                metadata={"source": "neo4j"}
            ))
        
        return entities
    except Exception as e:
        print(f"Neo4j query error: {e}")
        return []


async def search_knowledge_graph(query_text: str) -> List[BiomedicalEntity]:
    """
    Full-text search across the knowledge graph.
    """
    client = get_neo4j_client()
    if not client:
        return []
    
    # Simple name-based search (could use full-text index)
    query = """
    MATCH (n)
    WHERE toLower(n.name) CONTAINS toLower($query)
    RETURN n.id AS id, n.name AS name, labels(n) AS labels
    LIMIT 20
    """
    
    try:
        results = await client.execute_read(query, {"query": query_text})
        
        entities = []
        for row in results:
            entity_type = _infer_entity_type(row.get("labels", []))
            entities.append(BiomedicalEntity(
                id=row.get("id", f"neo4j:{row.get('name', '').lower()}"),
                name=row.get("name", ""),
                entity_type=entity_type,
                extraction_method=ExtractionMethod.MANUAL,
                extraction_confidence=0.8,
                metadata={"source": "neo4j"}
            ))
        
        return entities
    except Exception as e:
        print(f"Neo4j query error: {e}")
        return []


class GraphContext(TypedDict):
    """Pre-loaded graph context for the orchestrator."""
    drug_targets: List[BiomedicalEntity]
    disease_genes: List[BiomedicalEntity]
    pathway_edges: List[BiologicalEdge]
    neighbors: List[BiomedicalEntity]


async def load_graph_context_for_query(
    drug_name: Optional[str],
    disease_name: Optional[str]
) -> GraphContext:
    """
    Pre-load all relevant graph data for a drug repurposing query.
    """
    context: GraphContext = {
        "drug_targets": [],
        "disease_genes": [],
        "pathway_edges": [],
        "neighbors": []
    }
    
    if drug_name:
        context["drug_targets"] = await get_drug_targets(drug_name)
        context["neighbors"].extend(await get_entity_neighbors(drug_name, max_depth=1))
    
    if disease_name:
        context["disease_genes"] = await get_disease_genes(disease_name)
        context["neighbors"].extend(await get_entity_neighbors(disease_name, max_depth=1))
    
    if drug_name and disease_name:
        context["pathway_edges"] = await get_pathway_edges(drug_name, disease_name)
    
    return context


# =============================================================================
# Ingestion Functions (WRITE) - Idempotent Upserts
# =============================================================================

async def upsert_drug(name: str) -> bool:
    """Safely upsert a Drug node."""
    client = get_neo4j_client()
    if not client: return False
    
    query = """
    MERGE (n:Drug {name: $name})
    ON CREATE SET n.id = toLower($name), n.created_at = datetime()
    """
    try:
        await client.execute_write(query, {"name": name})
        return True
    except Exception as e:
        print(f"Upsert drug failed: {e}")
        return False

async def upsert_disease(name: str) -> bool:
    """Safely upsert a Disease node."""
    client = get_neo4j_client()
    if not client: return False
    
    query = """
    MERGE (n:Disease {name: $name})
    ON CREATE SET n.id = toLower($name), n.created_at = datetime()
    """
    try:
        await client.execute_write(query, {"name": name})
        return True
    except Exception as e:
        print(f"Upsert disease failed: {e}")
        return False

async def upsert_pathway(name: str) -> bool:
    """Safely upsert a Pathway node."""
    client = get_neo4j_client()
    if not client: return False
    
    query = """
    MERGE (n:Pathway {name: $name})
    ON CREATE SET n.id = toLower($name), n.created_at = datetime()
    """
    try:
        await client.execute_write(query, {"name": name})
        return True
    except Exception as e:
        print(f"Upsert pathway failed: {e}")
        return False

async def upsert_gene(name: str) -> bool:
    """Safely upsert a Gene node."""
    client = get_neo4j_client()
    if not client: return False
    
    query = """
    MERGE (n:Gene {name: $name})
    ON CREATE SET n.id = toLower($name), n.created_at = datetime()
    """
    try:
        await client.execute_write(query, {"name": name})
        return True
    except Exception as e:
        print(f"Upsert gene failed: {e}")
        return False

async def upsert_relation(
    source_name: str,
    source_type: str,
    relation: str,
    target_name: str,
    target_type: str,
    confidence: float,
    pmid: str,
    extraction_method: str = "auto"
) -> bool:
    """
    Safely upsert a relationship.
    
    Features:
    - Creates nodes if missing
    - Merges relationship
    - Updates confidence if new is higher
    - Appends uniqe PMIDs to support list
    """
    client = get_neo4j_client()
    if not client: return False
    
    # Sanitize types for Cypher label injection (can't parameterize labels)
    valid_labels = {"Drug", "Disease", "Gene", "Protein", "Pathway"}
    s_label = source_type.capitalize() if source_type.capitalize() in valid_labels else "Entity"
    t_label = target_type.capitalize() if target_type.capitalize() in valid_labels else "Entity"
    
    # Sanitize relation type
    valid_relations = {
        "TARGETS", "INHIBITS", "ACTIVATES", "BINDS", "REGULATES", 
        "ASSOCIATED_WITH", "TREATS", "CAUSES", "PREVENTS", "PARTICIPATES_IN"
    }
    rel_type = relation.upper().replace(" ", "_")
    if rel_type not in valid_relations:
        rel_type = "ASSOCIATED_WITH"  # Fallback
        
    query = f"""
    MERGE (s:{s_label} {{name: $s_name}})
    ON CREATE SET s.id = toLower($s_name)
    MERGE (t:{t_label} {{name: $t_name}})
    ON CREATE SET t.id = toLower($t_name)
    
    MERGE (s)-[r:{rel_type}]->(t)
    ON CREATE SET 
        r.confidence = $confidence, 
        r.pmids = [$pmid],
        r.extraction_method = $method,
        r.created_at = datetime()
    ON MATCH SET
        r.pmids = CASE 
            WHEN NOT $pmid IN r.pmids THEN r.pmids + $pmid 
            ELSE r.pmids 
        END,
        r.confidence = CASE 
            WHEN $confidence > r.confidence THEN $confidence 
            ELSE r.confidence 
        END
    """
    
    params = {
        "s_name": source_name,
        "t_name": target_name,
        "confidence": confidence,
        "pmid": pmid,
        "method": extraction_method
    }
    
    try:
        await client.execute_write(query, params)
        return True
    except Exception as e:
        print(f"Upsert relation failed: {e}")
        return False


# =============================================================================
# Helper Functions
# =============================================================================

def _infer_entity_type(labels: List[str]) -> EntityType:
    """Infer EntityType from Neo4j node labels."""
    labels_lower = [l.lower() for l in labels]
    
    if "drug" in labels_lower or "compound" in labels_lower:
        return EntityType.DRUG
    elif "disease" in labels_lower or "condition" in labels_lower:
        return EntityType.DISEASE
    elif "gene" in labels_lower:
        return EntityType.GENE
    elif "protein" in labels_lower:
        return EntityType.PROTEIN
    elif "pathway" in labels_lower:
        return EntityType.PATHWAY
    else:
        return EntityType.PATHWAY  # Default


def _map_relation_type(rel_type: str) -> RelationType:
    """Map Neo4j relationship type to RelationType enum."""
    mapping = {
        "TARGETS": RelationType.MODULATES,
        "INHIBITS": RelationType.INHIBITS,
        "ACTIVATES": RelationType.ACTIVATES,
        "BINDS": RelationType.BINDS,
        "MODULATES": RelationType.MODULATES,
        "REGULATES": RelationType.REGULATES,
        "UPREGULATES": RelationType.UPREGULATES,
        "DOWNREGULATES": RelationType.DOWNREGULATES,
        "ASSOCIATED_WITH": RelationType.ASSOCIATES_WITH,
        "TREATS": RelationType.TREATS,
        "CAUSES": RelationType.CAUSES,
        "PREVENTS": RelationType.PREVENTS,
    }
    return mapping.get(rel_type.upper(), RelationType.UNKNOWN)
