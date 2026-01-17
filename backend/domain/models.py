"""
BioMind Nexus - Domain Models

Core domain entities for the knowledge graph.
Used by DAL, Ingestion, and Agents (via encapsulation).
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

# Using Literal for strict type checking
EntityType = Literal["drug", "disease", "gene", "protein", "pathway", "unknown"]
RelationType = Literal[
    "TARGETS", "INHIBITS", "ACTIVATES", "BINDS", "REGULATES", "UPREGULATES", "DOWNREGULATES",
    "ASSOCIATED_WITH", "TREATS", "CAUSES", "PREVENTS", "PARTICIPATES_IN", "UNKNOWN"
]

class GraphNode(BaseModel):
    """A node in the biomedical knowledge graph."""
    id: str  # Unique ID (e.g., db_id or normalized name)
    name: str
    entity_type: EntityType
    metadata: Dict[str, str] = Field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)


class GraphEdge(BaseModel):
    """A directed edge representing a biological relationship."""
    source_id: str
    target_id: str
    relation: RelationType
    confidence: float = 1.0
    evidence_pmids: List[str] = Field(default_factory=list)
    extraction_method: str = "manual"  # manual, biobert, rule_based
    
    def __hash__(self):
        return hash((self.source_id, self.target_id, self.relation))


class GraphContext(BaseModel):
    """
    Sub-graph relevant to a specific query.
    Loaded from Neo4j and passed to agents.
    """
    nodes: Dict[str, GraphNode] = Field(default_factory=dict)
    edges: List[GraphEdge] = Field(default_factory=list)
    
    def add_node(self, node: GraphNode):
        self.nodes[node.id] = node
        
    def add_edge(self, edge: GraphEdge):
        self.edges.append(edge)
        
    @property
    def drug_targets(self) -> List[GraphNode]:
        """Helper: Get drug targets."""
        # This implementation requires knowing which nodes are targets. 
        # Typically filtered by relation type in DAL.
        return [n for n in self.nodes.values() if n.entity_type in ("gene", "protein")]

    @property
    def disease_genes(self) -> List[GraphNode]:
        """Helper: Get disease genes."""
        return [n for n in self.nodes.values() if n.entity_type in ("gene", "protein")]
