"""
BioMind Nexus - Agent Tests

Comprehensive tests for the drug repurposing agent layer.
Tests schema validation, agent purity, and workflow execution.

Run with: pytest tests/test_agents.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from backend.agents.schemas import (
    AgentState,
    DrugRepurposingQuery,
    BiomedicalEntity,
    EntityType,
    DrugCandidate,
    EvidenceItem,
    EvidenceType,
    Citation,
    SafetyCheck,
    SafetyFlag,
    Severity,
    MechanismPath,
)
from backend.agents.entity_extraction import EntityExtractionAgent
from backend.agents.literature import LiteratureAgent
from backend.agents.reasoning import ReasoningAgent
from backend.agents.ranking import RankingAgent
from backend.agents.safety import SafetyAgent
from backend.agents.base_agent import InputValidationError


# =============================================================================
# Schema Tests
# =============================================================================

class TestDrugRepurposingQuery:
    """Tests for input query schema."""
    
    def test_valid_query(self):
        """Valid query should parse correctly."""
        query = DrugRepurposingQuery(
            query_id="q123",
            raw_query="Can metformin be repurposed for breast cancer?"
        )
        assert query.query_id == "q123"
        assert "metformin" in query.raw_query
    
    def test_empty_query_rejected(self):
        """Empty query should raise validation error."""
        with pytest.raises(ValueError):
            DrugRepurposingQuery(query_id="q123", raw_query="")
    
    def test_whitespace_query_rejected(self):
        """Whitespace-only query should raise validation error."""
        with pytest.raises(ValueError):
            DrugRepurposingQuery(query_id="q123", raw_query="   ")
    
    def test_default_values(self):
        """Default values should be set correctly."""
        query = DrugRepurposingQuery(
            query_id="q123",
            raw_query="test query"
        )
        assert query.max_candidates == 10
        assert query.min_confidence == 0.5
        assert query.include_experimental is False


class TestBiomedicalEntity:
    """Tests for entity schema."""
    
    def test_entity_immutability(self):
        """Entity should be immutable (frozen)."""
        entity = BiomedicalEntity(
            id="drug:metformin",
            name="Metformin",
            entity_type=EntityType.DRUG
        )
        with pytest.raises(Exception):  # Pydantic ValidationError for frozen
            entity.name = "Changed"


class TestDrugCandidate:
    """Tests for drug candidate output schema."""
    
    def test_evidence_count_property(self):
        """Evidence count should calculate correctly."""
        candidate = DrugCandidate(
            candidate_id="c1",
            drug=BiomedicalEntity(id="d1", name="Drug", entity_type=EntityType.DRUG),
            target_disease=BiomedicalEntity(id="dis1", name="Disease", entity_type=EntityType.DISEASE),
            hypothesis="Test hypothesis",
            mechanism_summary="Test mechanism",
            overall_score=0.8,
            confidence=0.7,
            evidence_items=[
                EvidenceItem(evidence_id="e1", evidence_type=EvidenceType.LITERATURE, description="test", confidence=0.8),
                EvidenceItem(evidence_id="e2", evidence_type=EvidenceType.LITERATURE, description="test", confidence=0.9),
            ]
        )
        assert candidate.evidence_count == 2


# =============================================================================
# Agent Tests
# =============================================================================

class TestEntityExtractionAgent:
    """Tests for EntityExtractionAgent."""
    
    def test_agent_initialization(self):
        """Agent should initialize with correct metadata."""
        agent = EntityExtractionAgent()
        assert agent.name == "entity_extraction_agent"
        assert agent.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_extracts_drug(self):
        """Should extract drug entities from query."""
        agent = EntityExtractionAgent()
        query = DrugRepurposingQuery(
            query_id="q1",
            raw_query="Can metformin help with diabetes?"
        )
        state: AgentState = {"query": query}
        
        result = await agent.invoke(state)
        
        assert "extracted_entities" in result
        entities = result["extracted_entities"]
        drug_names = [e.name.lower() for e in entities if e.entity_type == EntityType.DRUG]
        assert "metformin" in drug_names
    
    @pytest.mark.asyncio
    async def test_extracts_disease(self):
        """Should extract disease entities from query."""
        agent = EntityExtractionAgent()
        query = DrugRepurposingQuery(
            query_id="q1",
            raw_query="Treatment options for breast cancer"
        )
        state: AgentState = {"query": query}
        
        result = await agent.invoke(state)
        
        entities = result["extracted_entities"]
        disease_entities = [e for e in entities if e.entity_type == EntityType.DISEASE]
        assert len(disease_entities) > 0
    
    @pytest.mark.asyncio
    async def test_extracts_genes(self):
        """Should extract gene entities from query."""
        agent = EntityExtractionAgent()
        query = DrugRepurposingQuery(
            query_id="q1",
            raw_query="BRCA1 and TP53 mutations in cancer"
        )
        state: AgentState = {"query": query}
        
        result = await agent.invoke(state)
        
        entities = result["extracted_entities"]
        gene_entities = [e for e in entities if e.entity_type == EntityType.GENE]
        gene_names = [e.name for e in gene_entities]
        assert "BRCA1" in gene_names
        assert "TP53" in gene_names


class TestLiteratureAgent:
    """Tests for LiteratureAgent."""
    
    def test_agent_initialization(self):
        """Agent should initialize with correct metadata."""
        agent = LiteratureAgent()
        assert agent.name == "literature_agent"
        assert agent.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_returns_evidence(self):
        """Should return evidence items for known entities."""
        agent = LiteratureAgent()
        query = DrugRepurposingQuery(query_id="q1", raw_query="metformin cancer")
        metformin = BiomedicalEntity(id="drug:metformin", name="Metformin", entity_type=EntityType.DRUG)
        
        state: AgentState = {
            "query": query,
            "extracted_entities": [metformin]
        }
        
        result = await agent.invoke(state)
        
        assert "literature_evidence" in result
        assert "literature_citations" in result
        assert len(result["literature_evidence"]) > 0


class TestReasoningAgent:
    """Tests for ReasoningAgent."""
    
    def test_agent_initialization(self):
        """Agent should initialize with correct metadata."""
        agent = ReasoningAgent()
        assert agent.name == "reasoning_agent"
        assert agent.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_generates_candidates(self):
        """Should generate drug candidates when evidence exists."""
        agent = ReasoningAgent()
        query = DrugRepurposingQuery(query_id="q1", raw_query="metformin cancer")
        drug = BiomedicalEntity(id="drug:metformin", name="Metformin", entity_type=EntityType.DRUG)
        disease = BiomedicalEntity(id="disease:cancer", name="Cancer", entity_type=EntityType.DISEASE)
        evidence = EvidenceItem(
            evidence_id="e1",
            evidence_type=EvidenceType.LITERATURE,
            description="Metformin shows anti-cancer effects",
            confidence=0.85,
            entities_mentioned=[drug]
        )
        
        state: AgentState = {
            "query": query,
            "extracted_entities": [drug, disease],
            "literature_evidence": [evidence],
            "literature_citations": []
        }
        
        result = await agent.invoke(state)
        
        assert "drug_candidates" in result
        assert "mechanism_paths" in result


class TestRankingAgent:
    """Tests for RankingAgent."""
    
    def test_agent_initialization(self):
        """Agent should initialize with correct metadata."""
        agent = RankingAgent()
        assert agent.name == "ranking_agent"
    
    @pytest.mark.asyncio
    async def test_ranks_candidates(self):
        """Should rank candidates by score."""
        agent = RankingAgent()
        query = DrugRepurposingQuery(query_id="q1", raw_query="test", min_confidence=0.3)
        
        drug = BiomedicalEntity(id="d1", name="Drug", entity_type=EntityType.DRUG)
        disease = BiomedicalEntity(id="dis1", name="Disease", entity_type=EntityType.DISEASE)
        
        candidates = [
            DrugCandidate(
                candidate_id="c1", drug=drug, target_disease=disease,
                hypothesis="H1", mechanism_summary="M1",
                overall_score=0.5, confidence=0.6
            ),
            DrugCandidate(
                candidate_id="c2", drug=drug, target_disease=disease,
                hypothesis="H2", mechanism_summary="M2",
                overall_score=0.9, confidence=0.8
            ),
        ]
        
        state: AgentState = {"query": query, "drug_candidates": candidates}
        result = await agent.invoke(state)
        
        ranked = result["ranked_candidates"]
        assert ranked[0].overall_score >= ranked[-1].overall_score


class TestSafetyAgent:
    """Tests for SafetyAgent."""
    
    def test_agent_initialization(self):
        """Agent should initialize with correct metadata."""
        agent = SafetyAgent()
        assert agent.name == "safety_agent"
        assert agent.MIN_CONFIDENCE_THRESHOLD == 0.3
    
    @pytest.mark.asyncio
    async def test_flags_low_confidence(self):
        """Should flag candidates with low confidence."""
        agent = SafetyAgent()
        query = DrugRepurposingQuery(query_id="q1", raw_query="test")
        
        drug = BiomedicalEntity(id="d1", name="Drug", entity_type=EntityType.DRUG)
        disease = BiomedicalEntity(id="dis1", name="Disease", entity_type=EntityType.DISEASE)
        
        low_confidence_candidate = DrugCandidate(
            candidate_id="c1", drug=drug, target_disease=disease,
            hypothesis="Test", mechanism_summary="Test",
            overall_score=0.3, confidence=0.2  # Below threshold
        )
        
        state: AgentState = {
            "query": query,
            "ranked_candidates": [low_confidence_candidate]
        }
        
        result = await agent.invoke(state)
        
        safety_result = result["safety_result"]
        assert len(safety_result.flags) > 0
        critical_flags = [f for f in safety_result.flags if f.severity == Severity.CRITICAL]
        assert len(critical_flags) > 0
    
    @pytest.mark.asyncio
    async def test_approves_valid_candidates(self):
        """Should approve candidates that pass all checks."""
        agent = SafetyAgent()
        query = DrugRepurposingQuery(query_id="q1", raw_query="test")
        
        drug = BiomedicalEntity(id="d1", name="Drug", entity_type=EntityType.DRUG)
        disease = BiomedicalEntity(id="dis1", name="Disease", entity_type=EntityType.DISEASE)
        
        valid_candidate = DrugCandidate(
            candidate_id="c1", drug=drug, target_disease=disease,
            hypothesis="Valid hypothesis",
            mechanism_summary="Valid mechanism",
            overall_score=0.8, confidence=0.7,
            mechanism_paths=[MechanismPath(
                path_id="p1",
                nodes=[drug, disease],
                edge_types=["treats"],
                confidence=0.7
            )],
            citations=[Citation(
                source_type="pubmed",
                source_id="12345",
                title="Test Paper",
                authors=["Author"]
            )]
        )
        
        state: AgentState = {
            "query": query,
            "ranked_candidates": [valid_candidate],
            "extracted_entities": [drug, disease],
            "literature_evidence": []
        }
        
        result = await agent.invoke(state)
        
        assert result["workflow_approved"] is True
        assert len(result["final_candidates"]) == 1


# =============================================================================
# Base Agent Tests
# =============================================================================

class TestBaseAgent:
    """Tests for base agent validation."""
    
    @pytest.mark.asyncio
    async def test_input_validation_fails_for_missing_keys(self):
        """Should raise error when required inputs are missing."""
        agent = EntityExtractionAgent()
        state: AgentState = {}  # Missing 'query'
        
        with pytest.raises(InputValidationError):
            await agent.invoke(state)
    
    @pytest.mark.asyncio
    async def test_tracks_step_history(self):
        """Should track execution in step_history."""
        agent = EntityExtractionAgent()
        query = DrugRepurposingQuery(query_id="q1", raw_query="test query")
        state: AgentState = {"query": query}
        
        result = await agent.invoke(state)
        
        assert "step_history" in result
        assert agent.name in result["step_history"]
