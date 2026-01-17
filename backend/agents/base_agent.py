"""
BioMind Nexus - Base Agent Class

Abstract base class for all specialized agents.
Defines the common interface and shared functionality.

Design Principles:
- Agents are stateless executors
- All state is passed through AgentState dict
- Agents request data through service layers, never directly from DBs
- All agent actions are auditable
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from backend.agents.schemas import AgentState, AgentResponse


class BaseAgent(ABC):
    """
    Abstract base class for BioMind Nexus agents.
    
    All specialized agents (Literature, Reasoning, Safety) inherit from this class.
    
    Attributes:
        name: Unique identifier for the agent
        description: Human-readable description of agent purpose
        version: Semantic version for tracking agent behavior changes
    """
    
    name: str = "base_agent"
    description: str = "Abstract base agent"
    version: str = "0.1.0"
    
    def __init__(self):
        """Initialize the agent with any required services."""
        self._initialize_services()
    
    def _initialize_services(self):
        """
        Initialize service layer connections.
        
        Subclasses override to inject required services.
        Agents should NEVER initialize database connections directly.
        """
        pass
    
    @abstractmethod
    async def invoke(self, state: AgentState) -> AgentState:
        """
        Execute the agent's primary function.
        
        Args:
            state: Current execution state containing query and context
        
        Returns:
            Updated state with agent's response added
        
        This method MUST:
        1. Validate input state
        2. Execute agent logic
        3. Update state with results
        4. Return modified state for next node
        """
        raise NotImplementedError("Subclasses must implement invoke()")
    
    def _create_response(
        self,
        content: Any,
        confidence: float = 1.0,
        citations: Optional[list] = None,
        metadata: Optional[Dict] = None
    ) -> AgentResponse:
        """
        Create a standardized agent response.
        
        Args:
            content: The primary response content
            confidence: Confidence score (0.0 - 1.0)
            citations: List of source citations
            metadata: Additional response metadata
        
        Returns:
            Structured AgentResponse
        """
        return AgentResponse(
            agent_name=self.name,
            agent_version=self.version,
            timestamp=datetime.utcnow().isoformat(),
            content=content,
            confidence=confidence,
            citations=citations or [],
            metadata=metadata or {}
        )
    
    def _log_execution(self, state: AgentState, duration_ms: float):
        """
        Log agent execution for audit trail.
        
        Called automatically after invoke() completes.
        """
        # TODO: Integrate with audit service
        pass
