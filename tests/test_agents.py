"""
BioMind Nexus - Agent Tests

Unit tests for agent functionality.
Tests agent initialization, state handling, and response formatting.

Run with: pytest tests/test_agents.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents.schemas import AgentState, QueryType
from backend.agents.literature import LiteratureAgent
from backend.agents.reasoning import ReasoningAgent
from backend.agents.safety import SafetyAgent


class TestLiteratureAgent:
    """Tests for LiteratureAgent."""
    
    def test_agent_initialization(self):
        """Agent should initialize with correct metadata."""
        agent = LiteratureAgent()
        
        assert agent.name == "literature_agent"
        assert agent.version == "0.1.0"
    
    @pytest.mark.asyncio
    async def test_invoke_returns_state(self):
        """Invoke should return updated state with response."""
        agent = LiteratureAgent()
        state: AgentState = {
            "query": "BRCA1 breast cancer",
            "query_type": QueryType.LITERATURE,
        }
        
        result = await agent.invoke(state)
        
        assert "literature_response" in result
        assert "entities_extracted" in result


class TestReasoningAgent:
    """Tests for ReasoningAgent."""
    
    def test_agent_initialization(self):
        """Agent should initialize with correct metadata."""
        agent = ReasoningAgent()
        
        assert agent.name == "reasoning_agent"
        assert agent.version == "0.1.0"
    
    @pytest.mark.asyncio
    async def test_invoke_returns_state(self):
        """Invoke should return updated state with response."""
        agent = ReasoningAgent()
        state: AgentState = {
            "query": "What is the mechanism linking EGFR to lung cancer?",
            "query_type": QueryType.REASONING,
        }
        
        result = await agent.invoke(state)
        
        assert "reasoning_response" in result


class TestSafetyAgent:
    """Tests for SafetyAgent."""
    
    def test_agent_initialization(self):
        """Agent should initialize with correct metadata."""
        agent = SafetyAgent()
        
        assert agent.name == "safety_agent"
        assert agent.CONFIDENCE_THRESHOLD == 0.5
    
    @pytest.mark.asyncio
    async def test_low_confidence_flagged(self):
        """Low confidence responses should be flagged."""
        agent = SafetyAgent()
        
        # Create a mock response with low confidence
        mock_response = MagicMock()
        mock_response.confidence = 0.3
        
        state: AgentState = {
            "literature_response": mock_response,
        }
        
        result = await agent.invoke(state)
        
        assert "safety_result" in result
        # Should flag low confidence
        safety_result = result["safety_result"]
        assert len(safety_result.flags) > 0
