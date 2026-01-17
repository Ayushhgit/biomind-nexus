"""
BioMind Nexus - Agent Schemas

Pydantic models and TypedDicts for agent state and responses.
All agent communication uses these typed structures.

Design: Strict typing enables validation and consistent interfaces.
"""

from enum import Enum
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Types of queries for agent routing."""
    LITERATURE = "literature"
    REASONING = "reasoning"
    HYBRID = "hybrid"


class AgentState(TypedDict, total=False):
    """
    Shared state passed between agents in the execution graph.
    
    This TypedDict defines all possible state keys.
    Agents read from and write to this shared state.
    """
    # Input
    query: str
    query_type: QueryType
    filters: Dict[str, Any]
    user_id: str
    request_id: str
    
    # Literature agent outputs
    literature_response: "AgentResponse"
    entities_extracted: List[Dict[str, Any]]
    
    # Reasoning agent outputs
    reasoning_response: "AgentResponse"
    
    # Safety agent outputs
    safety_result: "SafetyCheck"
    final_response_approved: bool


class Citation(BaseModel):
    """Citation for a source document."""
    source_type: str = Field(..., description="pubmed, biorxiv, etc.")
    source_id: str = Field(..., description="PMID, DOI, etc.")
    title: str
    authors: List[str]
    year: int
    url: Optional[str] = None
    excerpt: Optional[str] = Field(None, description="Relevant text excerpt")


class AgentResponse(BaseModel):
    """Standardized response from any agent."""
    agent_name: str
    agent_version: str
    timestamp: str
    content: Any = Field(..., description="Primary response content")
    confidence: float = Field(..., ge=0.0, le=1.0)
    citations: List[Citation] = []
    metadata: Dict[str, Any] = {}


class Hypothesis(BaseModel):
    """A generated hypothesis with supporting evidence."""
    statement: str = Field(..., description="The hypothesis text")
    entities_involved: List[str] = Field(..., description="Entity IDs")
    mechanism: Optional[str] = Field(None, description="Proposed mechanism")
    plausibility_score: float = Field(..., ge=0.0, le=1.0)
    supporting_paths: List[Dict[str, Any]] = []


class SafetyFlag(BaseModel):
    """A safety concern identified during validation."""
    type: str = Field(..., description="Category of flag")
    severity: str = Field(..., description="info, warning, critical")
    message: str


class SafetyCheck(BaseModel):
    """Result of safety validation."""
    passed: bool
    requires_human_review: bool = False
    flags: List[SafetyFlag] = []
