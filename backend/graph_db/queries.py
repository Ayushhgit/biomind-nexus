"""
BioMind Nexus - Graph Queries

Pre-defined Cypher queries for common graph operations.
All queries are parameterized to prevent injection.

Usage:
    from backend.graph_db.queries import GraphQueries
    
    result = await neo4j_client.execute_read(
        GraphQueries.FIND_GENE_DISEASE_PATHS,
        {"gene_id": "BRCA1", "max_depth": 3}
    )
"""


class GraphQueries:
    """
    Collection of parameterized Cypher queries.
    
    All queries use named parameters for safety.
    Query names follow VERB_NOUN pattern.
    """
    
    # =========================================================================
    # Entity Retrieval
    # =========================================================================
    
    GET_GENE_BY_ID = """
        MATCH (g:Gene {id: $gene_id})
        RETURN g
    """
    
    GET_DISEASE_BY_ID = """
        MATCH (d:Disease {id: $disease_id})
        RETURN d
    """
    
    SEARCH_ENTITIES_BY_NAME = """
        CALL db.index.fulltext.queryNodes('entity_names', $search_term)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
    """
    
    # =========================================================================
    # Relationship Queries
    # =========================================================================
    
    FIND_GENE_DISEASE_ASSOCIATIONS = """
        MATCH (g:Gene {id: $gene_id})-[r:ASSOCIATED_WITH]->(d:Disease)
        RETURN g, r, d
        ORDER BY r.score DESC
        LIMIT $limit
    """
    
    FIND_DRUG_TARGETS = """
        MATCH (dr:Drug {id: $drug_id})-[r:TARGETS]->(g:Gene)
        RETURN dr, r, g
        ORDER BY r.score DESC
    """
    
    # =========================================================================
    # Path Finding
    # =========================================================================
    
    FIND_SHORTEST_PATH = """
        MATCH path = shortestPath(
            (start {id: $start_id})-[*..{max_depth}]-(end {id: $end_id})
        )
        RETURN path
    """
    
    FIND_GENE_DISEASE_PATHS = """
        MATCH path = (g:Gene {id: $gene_id})-[*1..{max_depth}]-(d:Disease)
        WHERE d.id = $disease_id
        RETURN path, length(path) AS path_length
        ORDER BY path_length
        LIMIT $limit
    """
    
    FIND_MECHANISTIC_PATHS = """
        MATCH path = (start:Gene {id: $gene_id})-[:REGULATES|INTERACTS_WITH*1..{depth}]->(end:Gene)
        WHERE end.id IN $target_genes
        RETURN path, 
               [r IN relationships(path) | r.score] AS edge_scores,
               reduce(s = 1.0, r IN relationships(path) | s * r.score) AS path_score
        ORDER BY path_score DESC
        LIMIT $limit
    """
    
    # =========================================================================
    # Subgraph Extraction
    # =========================================================================
    
    GET_ENTITY_NEIGHBORHOOD = """
        MATCH (center {id: $entity_id})-[r*1..{depth}]-(neighbor)
        WITH center, collect(DISTINCT neighbor) AS neighbors, collect(DISTINCT r) AS rels
        RETURN center, neighbors, rels
    """
    
    GET_SUBGRAPH_BY_ENTITIES = """
        MATCH (n)
        WHERE n.id IN $entity_ids
        WITH collect(n) AS nodes
        MATCH (a)-[r]-(b)
        WHERE a IN nodes AND b IN nodes
        RETURN collect(DISTINCT a) + collect(DISTINCT b) AS nodes,
               collect(DISTINCT r) AS relationships
    """
    
    # =========================================================================
    # Write Operations
    # =========================================================================
    
    CREATE_OR_UPDATE_GENE = """
        MERGE (g:Gene {id: $id})
        SET g.symbol = $symbol,
            g.name = $name,
            g.description = $description,
            g.updated_at = datetime()
        ON CREATE SET g.created_at = datetime()
        RETURN g
    """
    
    CREATE_ASSOCIATION = """
        MATCH (source {id: $source_id}), (target {id: $target_id})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r.score = $score,
            r.source = $source,
            r.updated_at = datetime()
        ON CREATE SET r.created_at = datetime()
        RETURN r
    """
