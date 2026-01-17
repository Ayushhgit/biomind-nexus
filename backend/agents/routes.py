"""
BioMind Nexus - Agent API Routes

REST API endpoints for the drug repurposing workflow.
Exposes the LangGraph agent pipeline to frontend clients.

Endpoints:
    POST /query     - Submit a drug repurposing query
    GET /query/{id} - Get query status/results (for async)
    GET /entities   - Get available entity types
"""

from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from backend.agents.schemas import (
    DrugRepurposingQuery,
    DrugCandidate,
    EvidenceItem,
    BiomedicalEntity,
    EntityType,
    SafetyCheck,
    Citation,
)
from backend.agents.graph import run_drug_repurposing_workflow


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class QueryRequest(BaseModel):
    """Input model for drug repurposing query."""
    query: str = Field(..., min_length=3, max_length=1000, description="Natural language query about drug repurposing")
    max_candidates: int = Field(default=10, ge=1, le=50, description="Maximum number of candidates to return")
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
    include_experimental: bool = Field(default=False, description="Include experimental/off-label drugs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Can metformin be repurposed for breast cancer treatment?",
                "max_candidates": 10,
                "min_confidence": 0.5,
                "include_experimental": False
            }
        }


class EntityResponse(BaseModel):
    """Entity information for API response."""
    id: str
    name: str
    entity_type: str
    confidence: float


class EvidenceResponse(BaseModel):
    """Evidence item for API response."""
    evidence_id: str
    description: str
    evidence_type: str
    confidence: float
    source: Optional[str] = None


class CandidateResponse(BaseModel):
    """Drug candidate for API response."""
    candidate_id: str
    drug_name: str
    target_disease: str
    hypothesis: str
    mechanism_summary: str
    overall_score: float
    confidence: float
    rank: int
    evidence_count: int
    citations: List[str] = []


class SafetyResponse(BaseModel):
    """Safety check result for API response."""
    passed: bool
    flags_count: int
    critical_count: int
    warnings: List[str] = []


class QueryResponse(BaseModel):
    """Complete response for drug repurposing query."""
    query_id: str
    status: str  # "completed", "processing", "failed"
    timestamp: str
    
    # Results
    entities: List[EntityResponse] = []
    evidence_items: List[EvidenceResponse] = []
    candidates: List[CandidateResponse] = []
    safety: Optional[SafetyResponse] = None
    
    # Workflow metadata
    approved: bool = False
    steps_completed: List[str] = []
    errors: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "q-12345",
                "status": "completed",
                "timestamp": "2024-01-17T12:00:00Z",
                "entities": [{"id": "drug:metformin", "name": "Metformin", "entity_type": "drug", "confidence": 0.95}],
                "candidates": [],
                "approved": True,
                "steps_completed": ["entity_extraction", "literature", "reasoning", "ranking", "safety"]
            }
        }


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/query", response_model=QueryResponse, summary="Submit Drug Repurposing Query")
async def submit_query(request: QueryRequest):
    """
    Submit a drug repurposing query for analysis.
    
    This endpoint runs the full agent pipeline:
    1. Entity Extraction - Identify drugs, diseases, genes
    2. Literature Search - Find relevant PubMed evidence
    3. Pathway Simulation - Model biological pathways
    4. Reasoning - Generate repurposing hypotheses
    5. Ranking - Score and rank candidates
    6. Safety - Validate and flag concerns
    
    Returns structured results with candidates, evidence, and safety flags.
    """
    query_id = f"q-{uuid4().hex[:8]}"
    
    try:
        # Build structured query
        query = DrugRepurposingQuery(
            query_id=query_id,
            raw_query=request.query,
            max_candidates=request.max_candidates,
            min_confidence=request.min_confidence,
            include_experimental=request.include_experimental,
        )
        
        # Execute workflow
        final_state = await run_drug_repurposing_workflow(
            query=query,
            user_id="api_user",  # Would come from auth in production
            request_id=query_id
        )
        
        # Cache results for report endpoints (audit, graph, citations, PDF)
        try:
            from backend.report_routes import cache_query_result
            cache_query_result(query_id, final_state)
        except ImportError:
            pass  # Report routes not available
        
        # Transform results to API response
        response = _transform_state_to_response(query_id, final_state)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@router.get("/entities/types", summary="Get Available Entity Types")
async def get_entity_types():
    """
    Get list of supported biomedical entity types.
    
    Useful for frontend dropdowns and filters.
    """
    return {
        "entity_types": [
            {"id": "drug", "label": "Drug/Compound", "description": "Pharmaceutical compounds"},
            {"id": "disease", "label": "Disease/Condition", "description": "Medical conditions"},
            {"id": "gene", "label": "Gene", "description": "Human genes"},
            {"id": "protein", "label": "Protein", "description": "Proteins and enzymes"},
            {"id": "pathway", "label": "Pathway", "description": "Biological pathways"},
        ]
    }


@router.get("/examples", summary="Get Example Queries")
async def get_example_queries():
    """
    Get example queries for the frontend.
    
    Helps users understand the system capabilities.
    """
    return {
        "examples": [
            {
                "query": "Can metformin be repurposed for breast cancer treatment?",
                "description": "Classic example - metformin has shown anti-cancer properties"
            },
            {
                "query": "What drugs targeting AMPK could help with diabetes complications?",
                "description": "Pathway-based query focusing on a specific target"
            },
            {
                "query": "Are there any anti-inflammatory drugs that could treat Alzheimer's?",
                "description": "Disease repurposing based on mechanism"
            },
            {
                "query": "Can existing HIV medications be used for COVID-19?",
                "description": "Viral disease repurposing"
            }
        ]
    }


# =============================================================================
# Response Transformers
# =============================================================================

def _transform_state_to_response(query_id: str, state: dict) -> QueryResponse:
    """Transform AgentState to API response."""
    
    # Extract entities
    entities = []
    for entity in state.get("extracted_entities", []):
        entities.append(EntityResponse(
            id=entity.id,
            name=entity.name,
            entity_type=entity.entity_type.value if hasattr(entity.entity_type, 'value') else str(entity.entity_type),
            confidence=entity.extraction_confidence or 0.8
        ))
    
    # Extract evidence
    evidence_items = []
    for evidence in state.get("literature_evidence", [])[:10]:  # Limit to 10
        evidence_items.append(EvidenceResponse(
            evidence_id=evidence.evidence_id,
            description=evidence.description[:200] if evidence.description else "",
            evidence_type=evidence.evidence_type.value if hasattr(evidence.evidence_type, 'value') else str(evidence.evidence_type),
            confidence=evidence.confidence,
            source=evidence.citation.source_id if evidence.citation else None
        ))
    
    # Extract candidates
    candidates = []
    for candidate in state.get("final_candidates", []):
        citations = []
        if hasattr(candidate, 'citations') and candidate.citations:
            citations = [c.source_id for c in candidate.citations[:5]]
        
        candidates.append(CandidateResponse(
            candidate_id=candidate.candidate_id,
            drug_name=candidate.drug.name,
            target_disease=candidate.target_disease.name,
            hypothesis=candidate.hypothesis[:300] if candidate.hypothesis else "",
            mechanism_summary=candidate.mechanism_summary[:300] if candidate.mechanism_summary else "",
            overall_score=candidate.overall_score,
            confidence=candidate.confidence,
            rank=candidate.rank or 0,
            evidence_count=candidate.evidence_count,
            citations=citations
        ))
    
    # Extract safety
    safety = None
    safety_result = state.get("safety_result")
    if safety_result:
        warnings = []
        critical_count = 0
        for flag in safety_result.flags[:5]:  # Limit to 5 flags
            if flag.severity.value == "critical":
                critical_count += 1
            warnings.append(f"[{flag.severity.value}] {flag.message}")
        
        safety = SafetyResponse(
            passed=safety_result.passed,
            flags_count=len(safety_result.flags),
            critical_count=critical_count,
            warnings=warnings
        )
    
    return QueryResponse(
        query_id=query_id,
        status="completed",
        timestamp=datetime.utcnow().isoformat() + "Z",
        entities=entities,
        evidence_items=evidence_items,
        candidates=candidates,
        safety=safety,
        approved=state.get("workflow_approved", False),
        steps_completed=state.get("step_history", []),
        errors=state.get("errors", [])
    )
