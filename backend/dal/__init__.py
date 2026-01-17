"""
Data Access Layer Package

Provides structured access to databases (Neo4j, Cassandra).
Agents access data through structured domain objects, not raw queries.

Architecture:
    API/Orchestrator → DAL → Structured Domain Objects → AgentState → Agents (PURE)
"""

from backend.dal.neo4j_dal import (
    get_drug_targets,
    get_disease_genes,
    get_pathway_edges,
    get_entity_neighbors,
    search_knowledge_graph,
    load_graph_context_for_query,
)

from backend.dal.cassandra_dal import (
    log_workflow_event,
    get_workflow_history,
)


__all__ = [
    # Neo4j Knowledge Graph
    "get_drug_targets",
    "get_disease_genes",
    "get_pathway_edges",
    "get_entity_neighbors",
    "search_knowledge_graph",
    "load_graph_context_for_query",
    
    # Cassandra Audit
    "log_workflow_event",
    "get_workflow_history",
]
