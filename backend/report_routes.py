"""
BioMind Nexus - Report Routes

API endpoints for post-query results display:
- Audit trail retrieval
- Reasoning graph data
- Citations list
- PDF report generation

Design: All data comes from pre-computed AgentState. No recomputation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import io

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


router = APIRouter(prefix="/reports", tags=["reports"])


# =============================================================================
# Response Models
# =============================================================================

class AuditStep(BaseModel):
    """Single step in the workflow audit trail."""
    step_name: str
    status: str  # "completed", "skipped", "failed"
    timestamp: str
    duration_ms: Optional[int] = None


class AuditTrailResponse(BaseModel):
    """Audit log for a query - governance and traceability."""
    workflow_id: str
    session_id: Optional[str] = None
    timestamp: str
    user_role: str
    steps_executed: List[AuditStep]
    safety_decision: str  # "approved", "flagged", "blocked"
    safety_reason: Optional[str] = None
    confidence_summary: float
    system_version: str = "1.0.0"
    model_identifiers: Dict[str, str] = Field(default_factory=dict)


class GraphNode(BaseModel):
    """Node in the reasoning subgraph."""
    id: str
    label: str
    node_type: str  # "drug", "target", "pathway", "disease"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Edge in the reasoning subgraph."""
    source: str
    target: str
    relation: str  # "INHIBITS", "ACTIVATES", "IMPLICATED_IN"
    confidence: float
    pmid: Optional[str] = None


class ReasoningGraphResponse(BaseModel):
    """Query-specific reasoning subgraph - only accepted paths."""
    query_id: str
    drug: str
    disease: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    path_count: int
    max_confidence: float


class CitationItem(BaseModel):
    """Single citation with evidence role."""
    pmid: str
    title: str
    year: Optional[int] = None
    authors: List[str] = Field(default_factory=list)
    evidence_role: str  # Which relationship this supports
    confidence: float
    url: str


class CitationsResponse(BaseModel):
    """All citations supporting the result."""
    query_id: str
    citations: List[CitationItem]
    total_count: int


# =============================================================================
# In-Memory Results Cache (for demo - production would use Redis/DB)
# =============================================================================

# Cache query results for retrieval by query_id
_results_cache: Dict[str, Dict[str, Any]] = {}


def cache_query_result(query_id: str, state: Dict[str, Any]):
    """Store query result for later retrieval."""
    _results_cache[query_id] = {
        "state": state,
        "timestamp": datetime.utcnow().isoformat()
    }


def get_cached_result(query_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached query result."""
    return _results_cache.get(query_id)


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/{query_id}/audit", response_model=AuditTrailResponse)
async def get_audit_trail(query_id: str):
    """
    Get audit trail for a query.
    
    Returns governance data: steps executed, safety decision, timestamps.
    Data comes from Cassandra audit logs (or cached state).
    """
    cached = get_cached_result(query_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Query result not found")
    
    state = cached["state"]
    
    # Build audit steps from step_history
    steps = []
    for step_name in state.get("step_history", []):
        steps.append(AuditStep(
            step_name=step_name,
            status="completed",
            timestamp=cached["timestamp"]
        ))
    
    # Extract safety decision
    safety_result = state.get("safety_result")
    safety_decision = "approved"
    safety_reason = None
    if safety_result:
        if not safety_result.passed:
            safety_decision = "blocked"
            if safety_result.flags:
                safety_reason = safety_result.flags[0].description
        elif safety_result.flags:
            safety_decision = "flagged"
            safety_reason = f"{len(safety_result.flags)} warning(s)"
    
    return AuditTrailResponse(
        workflow_id=query_id,
        session_id=state.get("request_id"),
        timestamp=cached["timestamp"],
        user_role=state.get("user_id", "researcher"),
        steps_executed=steps,
        safety_decision=safety_decision,
        safety_reason=safety_reason,
        confidence_summary=state.get("overall_confidence", 0.0),
        model_identifiers={
            "entity_extraction": "BioBERT",
            "evidence_scoring": "PubMedBERT",
            "llm": "Groq/Llama"
        }
    )


@router.get("/{query_id}/graph", response_model=ReasoningGraphResponse)
async def get_reasoning_graph(query_id: str):
    """
    Get the reasoning subgraph for visualization.
    
    CRITICAL: Graph is built ONLY from SimulationResult.valid_paths.
    - Nodes come from BiologicalEdge.source_entity and target_entity
    - Edges come from BiologicalEdge relations
    - NO text parsing, NO tokenization, NO fallback to raw entities
    
    Validation:
    - Stopwords are rejected
    - Relation labels cannot be nodes
    - Duplicates are merged by (name, type)
    """
    cached = get_cached_result(query_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Query result not found")
    
    state = cached["state"]
    simulation = state.get("simulation_result")
    query = state.get("query", {})
    
    # Extract drug/disease from query
    drug_name = "Unknown Drug"
    disease_name = "Unknown Disease"
    if hasattr(query, "source_drug") and query.source_drug:
        drug_name = query.source_drug.name
    if hasattr(query, "target_disease") and query.target_disease:
        disease_name = query.target_disease.name
    
    # Initialize graph structures with deduplication
    nodes_by_id: Dict[str, GraphNode] = {}
    edges_list: List[GraphEdge] = []
    edge_set: set = set()  # (source, target, relation, pmid) for dedup
    max_conf = 0.0
    
    # STOPWORDS - these must NEVER appear as nodes
    STOPWORDS = {
        "for", "be", "can", "may", "to", "the", "a", "an", "is", "are",
        "in", "on", "of", "with", "by", "and", "or", "as", "it", "this",
        "that", "have", "has", "was", "were", "been", "being", "do", "does",
        "did", "will", "would", "could", "should", "might", "must"
    }
    
    # RELATION LABELS - these must NEVER appear as nodes
    RELATION_LABELS = {
        "treats", "inhibits", "activates", "binds", "modulates",
        "upregulates", "downregulates", "phosphorylates", "catalyzes",
        "transports", "regulates", "associates_with", "causes",
        "prevents", "implicated_in", "unknown"
    }
    
    def _is_valid_entity(name: str) -> bool:
        """Check if entity name is valid (not stopword or relation)."""
        if not name or len(name.strip()) < 2:
            return False
        name_lower = name.lower().strip()
        if name_lower in STOPWORDS:
            return False
        if name_lower in RELATION_LABELS:
            return False
        # Reject pure numbers or single chars
        if name_lower.isdigit():
            return False
        return True
    
    def _normalize_id(name: str) -> str:
        """Create normalized node ID."""
        return name.lower().strip().replace(" ", "_").replace("-", "_")
    
    def _infer_entity_type(name: str, is_source: bool, edge_relation: str) -> str:
        """Infer entity type from context."""
        name_lower = name.lower()
        
        # Disease indicators
        if any(kw in name_lower for kw in ["cancer", "disease", "syndrome", "disorder", "carcinoma", "tumor", "diabetes"]):
            return "disease"
        
        # Pathway indicators
        if any(kw in name_lower for kw in ["pathway", "signaling", "cascade", "metabolism"]):
            return "pathway"
        
        # Target/Gene/Protein indicators
        if any(kw in name_lower for kw in ["receptor", "kinase", "enzyme", "protein", "gene", "ampk", "mtor", "egfr", "p53", "akt"]):
            return "target"
        
        # Drug indicators (common suffixes)
        if any(name_lower.endswith(suffix) for suffix in ["in", "ol", "ib", "ab", "ide", "ine", "one", "ate"]):
            if is_source and edge_relation.lower() in ["treats", "inhibits", "activates", "binds"]:
                return "drug"
        
        # Default based on position in path
        if is_source:
            return "drug"
        return "target"
    
    # BUILD GRAPH FROM SIMULATION RESULT ONLY
    if simulation and hasattr(simulation, "valid_paths"):
        for path in simulation.valid_paths:
            if not hasattr(path, "edges"):
                continue
                
            for edge in path.edges:
                # Get entity names from BiologicalEdge
                source_name = edge.source_entity if hasattr(edge, "source_entity") else ""
                target_name = edge.target_entity if hasattr(edge, "target_entity") else ""
                
                # VALIDATE entities
                if not _is_valid_entity(source_name) or not _is_valid_entity(target_name):
                    continue
                
                # Get relation
                relation = ""
                if hasattr(edge, "relation"):
                    relation = edge.relation.value if hasattr(edge.relation, "value") else str(edge.relation)
                
                # Get confidence and PMID
                confidence = edge.confidence if hasattr(edge, "confidence") else 0.5
                pmid = edge.pmid_support[0] if hasattr(edge, "pmid_support") and edge.pmid_support else None
                
                # Create normalized IDs
                src_id = _normalize_id(source_name)
                tgt_id = _normalize_id(target_name)
                
                # ADD SOURCE NODE (deduplicated)
                if src_id not in nodes_by_id:
                    nodes_by_id[src_id] = GraphNode(
                        id=src_id,
                        label=source_name.strip(),
                        node_type=_infer_entity_type(source_name, True, relation)
                    )
                
                # ADD TARGET NODE (deduplicated)
                if tgt_id not in nodes_by_id:
                    nodes_by_id[tgt_id] = GraphNode(
                        id=tgt_id,
                        label=target_name.strip(),
                        node_type=_infer_entity_type(target_name, False, relation)
                    )
                
                # ADD EDGE (deduplicated by source+target+relation+pmid)
                edge_key = (src_id, tgt_id, relation.upper(), pmid or "")
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges_list.append(GraphEdge(
                        source=src_id,
                        target=tgt_id,
                        relation=relation.upper(),
                        confidence=confidence,
                        pmid=pmid
                    ))
                
                max_conf = max(max_conf, confidence)
    
    # Convert to list
    nodes_list = list(nodes_by_id.values())
    
    # FINAL VALIDATION
    # Assert no stopwords slipped through
    for node in nodes_list:
        if node.label.lower() in STOPWORDS:
            raise HTTPException(
                status_code=500,
                detail=f"Validation failed: stopword '{node.label}' appeared as node"
            )
        if node.label.lower() in RELATION_LABELS:
            raise HTTPException(
                status_code=500,
                detail=f"Validation failed: relation '{node.label}' appeared as node"
            )
    
    return ReasoningGraphResponse(
        query_id=query_id,
        drug=drug_name,
        disease=disease_name,
        nodes=nodes_list,
        edges=edges_list,
        path_count=len(simulation.valid_paths) if simulation and hasattr(simulation, "valid_paths") else 0,
        max_confidence=max_conf
    )


@router.get("/{query_id}/citations", response_model=CitationsResponse)
async def get_citations(query_id: str):
    """
    Get citations supporting the result.
    
    Sorted by relevance to accepted pathways.
    Includes evidence role and confidence.
    """
    cached = get_cached_result(query_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Query result not found")
    
    state = cached["state"]
    
    citations = []
    evidence_items = state.get("literature_evidence", [])
    
    for ev in evidence_items:
        citation = ev.citation if hasattr(ev, "citation") else ev.get("citation")
        if not citation:
            continue
        
        # Determine evidence role from entities mentioned
        evidence_role = "general evidence"
        if hasattr(ev, "entities_mentioned") and ev.entities_mentioned:
            entity_names = [e.name for e in ev.entities_mentioned[:2]]
            if len(entity_names) >= 2:
                evidence_role = f"supports {entity_names[0]} → {entity_names[1]}"
            elif entity_names:
                evidence_role = f"mentions {entity_names[0]}"
        
        citations.append(CitationItem(
            pmid=citation.source_id if hasattr(citation, "source_id") else citation.get("source_id", ""),
            title=citation.title if hasattr(citation, "title") else citation.get("title", ""),
            year=citation.year if hasattr(citation, "year") else citation.get("year"),
            authors=citation.authors[:3] if hasattr(citation, "authors") else citation.get("authors", [])[:3],
            evidence_role=evidence_role,
            confidence=ev.confidence if hasattr(ev, "confidence") else ev.get("confidence", 0.5),
            url=citation.url if hasattr(citation, "url") else citation.get("url", "")
        ))
    
    # Sort by confidence descending
    citations.sort(key=lambda x: x.confidence, reverse=True)
    
    return CitationsResponse(
        query_id=query_id,
        citations=citations,
        total_count=len(citations)
    )


@router.get("/{query_id}/pdf")
async def download_pdf(query_id: str):
    """
    Generate and download PDF report.
    
    Includes: Cover page, query overview, graph, reasoning,
    citations, safety review, disclaimer.
    """
    cached = get_cached_result(query_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Query result not found")
    
    state = cached["state"]
    
    # Import PDF generator
    try:
        from backend.services.pdf_generator import generate_report_pdf
        pdf_bytes = generate_report_pdf(query_id, state, cached["timestamp"])
    except ImportError:
        # Fallback: simple text PDF
        pdf_bytes = _generate_simple_pdf(query_id, state, cached["timestamp"])
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=biomind_report_{query_id}.pdf"
        }
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _infer_node_type(name: str, position: str) -> str:
    """Infer node type from name or position."""
    name_lower = name.lower()
    
    # Check common patterns
    if any(kw in name_lower for kw in ["cancer", "disease", "syndrome", "disorder"]):
        return "disease"
    if any(kw in name_lower for kw in ["pathway", "signaling", "cascade"]):
        return "pathway"
    if any(kw in name_lower for kw in ["gene", "protein", "receptor", "kinase"]):
        return "target"
    
    # Default based on position
    if position == "source":
        return "drug"
    return "target"


def _generate_simple_pdf(query_id: str, state: dict, timestamp: str) -> bytes:
    """Generate a simple PDF without reportlab."""
    # This is a placeholder - actual PDF generation requires reportlab
    # Return a minimal PDF structure
    content = f"""BioMind Nexus Report
Query ID: {query_id}
Generated: {timestamp}

This is a placeholder PDF. Install reportlab for full PDF generation.
"""
    
    # Minimal PDF structure
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length {len(content)} >>
stream
BT /F1 12 Tf 50 700 Td ({content}) Tj ET
endstream
endobj
xref
0 5
trailer << /Size 5 /Root 1 0 R >>
startxref
0
%%EOF"""
    
    return pdf.encode("latin-1")
