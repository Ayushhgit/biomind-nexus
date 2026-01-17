"""
Schemas for all our agents.

We use Pydantic models for everything so we know the data is correct.
"""

from enum import Enum
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================

class QueryType(str, Enum):
    """Different types of queries."""
    DRUG_REPURPOSING = "drug_repurposing"
    LITERATURE = "literature"
    MECHANISM = "mechanism"


class EntityType(str, Enum):
    """Types of biological things."""
    DRUG = "drug"
    DISEASE = "disease"
    GENE = "gene"
    PROTEIN = "protein"
    PATHWAY = "pathway"
    PHENOTYPE = "phenotype"


class EvidenceType(str, Enum):
    """Where the evidence comes from."""
    LITERATURE = "literature"
    GRAPH_PATH = "graph_path"
    CLINICAL_TRIAL = "clinical_trial"
    MECHANISM = "mechanism"


class Severity(str, Enum):
    """How bad a safety flag is."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ExtractionMethod(str, Enum):
    """How we found the entity."""
    BIOBERT = "BioBERT"
    PUBMEDBERT = "PubMedBERT"
    LLM = "LLM"
    PATTERN = "pattern"
    MANUAL = "manual"


# =============================================================================
# Input Schemas
# =============================================================================

class BiomedicalEntity(BaseModel):
    """A drug, disease, or gene."""
    id: str = Field(..., description="Unique identifier (e.g., DrugBank ID, DOID)")
    name: str = Field(..., description="Human-readable name")
    entity_type: EntityType
    aliases: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Extraction provenance
    extraction_method: Optional[ExtractionMethod] = Field(
        default=None,
        description="Model/method used for extraction"
    )
    extraction_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score from extraction model"
    )
    
    class Config:
        frozen = True  # Immutable


class DrugRepurposingQuery(BaseModel):
    """
    The user's query formatted nicely.
    """
    query_id: str = Field(..., description="Unique query identifier for tracing")
    raw_query: str = Field(..., description="Original user query text")
    
    # Optional pre-extracted entities (can be populated by entity extraction agent)
    source_drug: Optional[BiomedicalEntity] = None
    target_disease: Optional[BiomedicalEntity] = None
    target_genes: List[BiomedicalEntity] = Field(default_factory=list)
    
    # Query constraints
    max_candidates: int = Field(default=10, ge=1, le=50)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    include_experimental: bool = Field(default=False)
    
    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @field_validator('raw_query')
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


# =============================================================================
# Evidence Schemas
# =============================================================================

class Citation(BaseModel):
    """A paper or article."""
    source_type: str = Field(..., description="pubmed, biorxiv, clinical_trial, etc.")
    source_id: str = Field(..., description="PMID, DOI, NCT number, etc.")
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    url: Optional[str] = None
    excerpt: Optional[str] = Field(None, description="Relevant text excerpt")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)


class MechanismPath(BaseModel):
    """
    A path from drug to disease in our graph.
    """
    path_id: str
    nodes: List[BiomedicalEntity] = Field(..., min_length=2)
    edge_types: List[str] = Field(..., description="Relationship types between nodes")
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_citations: List[Citation] = Field(default_factory=list)
    
    @property
    def path_length(self) -> int:
        return len(self.nodes) - 1
    
    def to_string(self) -> str:
        """Human-readable path representation."""
        parts = []
        for i, node in enumerate(self.nodes):
            parts.append(node.name)
            if i < len(self.edge_types):
                parts.append(f" --[{self.edge_types[i]}]--> ")
        return "".join(parts)


class EvidenceItem(BaseModel):
    """
    One piece of proof.
    """
    evidence_id: str
    evidence_type: EvidenceType
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Source-specific data
    citation: Optional[Citation] = None
    mechanism_path: Optional[MechanismPath] = None
    
    # Extracted entities
    entities_mentioned: List[BiomedicalEntity] = Field(default_factory=list)


# =============================================================================
# Output Schemas
# =============================================================================

class DrugCandidate(BaseModel):
    """
    A drug that might work for the disease.
    """
    candidate_id: str
    drug: BiomedicalEntity
    target_disease: BiomedicalEntity
    
    # The hypothesis
    hypothesis: str = Field(..., description="Clear statement of the repurposing hypothesis")
    mechanism_summary: str = Field(..., description="Brief explanation of proposed mechanism")
    
    # Scoring
    overall_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    novelty_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Supporting evidence
    mechanism_paths: List[MechanismPath] = Field(default_factory=list)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    
    # Ranking metadata
    rank: Optional[int] = None
    
    @property
    def evidence_count(self) -> int:
        return len(self.evidence_items)


class AgentResponse(BaseModel):
    """Standard response from an agent."""
    agent_name: str
    agent_version: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Response content (type depends on agent)
    content: Any = Field(..., description="Primary response content")
    
    # Quality metrics
    confidence: float = Field(..., ge=0.0, le=1.0)
    processing_time_ms: Optional[float] = None
    
    # Provenance
    citations: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Pathway Simulation Schemas
# =============================================================================

class RelationType(str, Enum):
    """How two things are related."""
    INHIBITS = "inhibits"
    ACTIVATES = "activates"
    BINDS = "binds"
    MODULATES = "modulates"
    UPREGULATES = "upregulates"
    DOWNREGULATES = "downregulates"
    PHOSPHORYLATES = "phosphorylates"
    CATALYZES = "catalyzes"
    TRANSPORTS = "transports"
    REGULATES = "regulates"
    ASSOCIATES_WITH = "associates_with"
    TREATS = "treats"
    CAUSES = "causes"
    PREVENTS = "prevents"
    UNKNOWN = "unknown"


class BiologicalEdge(BaseModel):
    """
    A connection between two entities in the graph.
    """
    source_entity: str = Field(..., description="Source entity identifier")
    target_entity: str = Field(..., description="Target entity identifier")
    relation: RelationType = Field(..., description="Type of biological relationship")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Edge confidence score")
    evidence_count: int = Field(default=0, ge=0, description="Number of supporting evidence items")
    pmid_support: List[str] = Field(default_factory=list, description="Supporting PubMed IDs")
    
    class Config:
        frozen = True
    
    def __hash__(self):
        return hash((self.source_entity, self.target_entity, self.relation))
    
    def __eq__(self, other):
        if not isinstance(other, BiologicalEdge):
            return False
        return (self.source_entity == other.source_entity and 
                self.target_entity == other.target_entity and 
                self.relation == other.relation)


class PathwayPath(BaseModel):
    """
    A full path from drug to disease.
    """
    path_id: str = Field(..., description="Unique path identifier")
    edges: List[BiologicalEdge] = Field(..., min_length=1, description="Ordered edges in path")
    biological_rationale: str = Field(..., description="Scientific explanation of path plausibility")
    path_confidence: float = Field(..., ge=0.0, le=1.0, description="Aggregated path confidence")
    path_length: int = Field(..., ge=1, description="Number of edges in path")
    evidence_support_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    @property
    def source(self) -> str:
        """Starting entity of the path."""
        return self.edges[0].source_entity if self.edges else ""
    
    @property
    def target(self) -> str:
        """Ending entity of the path."""
        return self.edges[-1].target_entity if self.edges else ""
    
    def to_string(self) -> str:
        """Human-readable path representation."""
        if not self.edges:
            return ""
        parts = [self.edges[0].source_entity]
        for edge in self.edges:
            parts.append(f" --[{edge.relation.value}]--> {edge.target_entity}")
        return "".join(parts)


class RejectedPath(BaseModel):
    """A path we threw away."""
    path_description: str = Field(..., description="Human-readable path description")
    rejection_reason: str = Field(..., description="Why this path was rejected")
    partial_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SimulationResult(BaseModel):
    """
    The results of our simulation.
    """
    simulation_id: str = Field(..., description="Unique simulation identifier")
    drug: str = Field(..., description="Drug entity name")
    disease: str = Field(..., description="Disease entity name")
    
    # Valid paths that passed all filters
    valid_paths: List[PathwayPath] = Field(default_factory=list)
    
    # Paths that were rejected with explanations
    rejected_paths: List[RejectedPath] = Field(default_factory=list)
    
    # Aggregate plausibility score
    overall_plausibility: float = Field(..., ge=0.0, le=1.0)
    
    # Simulation metadata
    entities_traversed: int = Field(default=0, ge=0)
    edges_evaluated: int = Field(default=0, ge=0)
    max_path_depth: int = Field(default=0, ge=0)
    
    @property
    def has_valid_paths(self) -> bool:
        return len(self.valid_paths) > 0
    
    @property
    def top_path(self) -> Optional[PathwayPath]:
        """Return highest confidence path."""
        if not self.valid_paths:
            return None
        return max(self.valid_paths, key=lambda p: p.path_confidence)


# =============================================================================
# Safety Schemas
# =============================================================================

class SafetyFlag(BaseModel):
    """Something that looks wrong."""
    flag_id: str
    flag_type: str = Field(..., description="Category: low_confidence, unsupported_claim, etc.")
    severity: Severity
    message: str
    source_agent: Optional[str] = None
    affected_field: Optional[str] = None


class SafetyCheck(BaseModel):
    """Final safety check results."""
    passed: bool
    requires_human_review: bool = False
    flags: List[SafetyFlag] = Field(default_factory=list)
    
    # Aggregated metrics
    min_confidence: Optional[float] = None
    total_citations: int = 0
    
    # Validation details
    schema_valid: bool = True
    content_safe: bool = True
    citations_verified: bool = True
    
    @property
    def critical_flags(self) -> List[SafetyFlag]:
        return [f for f in self.flags if f.severity == Severity.CRITICAL]
    
    @property
    def warning_flags(self) -> List[SafetyFlag]:
        return [f for f in self.flags if f.severity == Severity.WARNING]


# =============================================================================
# Workflow State
# =============================================================================

class AgentState(TypedDict, total=False):
    """
    The state that gets passed around between agents.
    It holds all the data.
    """
    # === Input ===
    query: DrugRepurposingQuery
    request_id: str
    user_id: str
    
    # === Pre-loaded Graph Context (from DAL) ===
    # Agents read this as given data; they don't know it came from Neo4j
    graph_drug_targets: List[BiomedicalEntity]
    graph_disease_genes: List[BiomedicalEntity]
    graph_pathway_edges: List[BiologicalEdge]
    graph_neighbors: List[BiomedicalEntity]
    
    # === Entity Extraction Agent Output ===
    extracted_entities: List[BiomedicalEntity]
    
    # === Literature Agent Output ===
    literature_evidence: List[EvidenceItem]
    literature_citations: List[Citation]
    
    # === Pathway Simulation Agent Output ===
    simulation_result: SimulationResult
    
    # === Reasoning Agent Output ===
    mechanism_paths: List[MechanismPath]
    drug_candidates: List[DrugCandidate]
    
    # === Ranking Agent Output ===
    ranked_candidates: List[DrugCandidate]
    
    # === Safety Agent Output ===
    safety_result: SafetyCheck
    
    # === Final Output ===
    final_candidates: List[DrugCandidate]
    workflow_approved: bool
    
    # === Workflow Metadata ===
    current_step: str
    step_history: List[str]
    errors: List[str]


