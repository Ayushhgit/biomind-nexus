"""
BioMind Nexus - Base Agent Class

Abstract base class for all specialized agents.
Enforces pure function design and output schema validation.

Design Principles (NON-NEGOTIABLE):
- Agents are PURE functions: input -> output
- Agents do NOT access databases
- Agents do NOT perform authentication
- Agents do NOT log directly
- All outputs must conform to Pydantic schemas
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, TypeVar
from datetime import datetime
import time

from pydantic import BaseModel, ValidationError

from backend.agents.schemas import AgentState, AgentResponse


T = TypeVar('T', bound=BaseModel)


class AgentError(Exception):
    """Base exception for agent errors."""
    pass


class InputValidationError(AgentError):
    """Raised when agent input fails validation."""
    pass


class OutputValidationError(AgentError):
    """Raised when agent output fails schema validation."""
    pass


class BaseAgent(ABC):
    """
    Abstract base class for BioMind Nexus agents.
    
    All specialized agents inherit from this class and implement
    the `process` method for their specific logic.
    
    Lifecycle:
    1. invoke() receives state
    2. _validate_input() checks required fields
    3. process() executes agent logic (implemented by subclass)
    4. _validate_output() enforces schema compliance
    5. Updated state returned
    
    Attributes:
        name: Unique identifier for the agent
        description: Human-readable description of agent purpose
        version: Semantic version for tracking agent behavior changes
    """
    
    name: str = "base_agent"
    description: str = "Abstract base agent"
    version: str = "0.1.0"
    
    # Subclasses define required input keys
    required_input_keys: list[str] = []
    
    # Subclasses define generated output keys
    output_keys: list[str] = []
    
    def __init__(self):
        """
        Initialize the agent.
        
        Note: Agents should NOT initialize database connections or
        external services. All data flows through AgentState.
        """
        pass
    
    async def invoke(self, state: AgentState) -> AgentState:
        """
        Execute the agent's primary function with validation.
        
        This is the main entry point called by LangGraph.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with agent outputs added
        
        Raises:
            InputValidationError: If required inputs are missing
            OutputValidationError: If outputs fail schema validation
        """
        start_time = time.perf_counter()
        
        # Track current step
        state["current_step"] = self.name
        if "step_history" not in state:
            state["step_history"] = []
        state["step_history"].append(self.name)
        
        # Validate input
        self._validate_input(state)
        
        # Execute agent logic (implemented by subclass)
        state = await self.process(state)
        
        # Validate output
        self._validate_output(state)
        
        # Add timing metadata
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        return state
    
    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """
        Execute the agent's core logic.
        Subclasses MUST implement this method.
        
        Args:
            state: Current workflow state with validated inputs
        
        Returns:
            Updated state with agent outputs
        """
        raise NotImplementedError("Subclasses must implement process()")
    
    def _validate_input(self, state: AgentState) -> None:
        """
        Validate that required inputs are present in state.
        
        Raises:
            InputValidationError: If required keys are missing
        """
        missing = []
        for key in self.required_input_keys:
            if key not in state or state[key] is None:
                missing.append(key)
        
        if missing:
            raise InputValidationError(
                f"Agent '{self.name}' missing required inputs: {missing}"
            )
    
    def _validate_output(self, state: AgentState) -> None:
        """
        Validate that agent outputs conform to schemas.
        
        Raises:
            OutputValidationError: If outputs fail validation
        """
        # Check output keys are present
        for key in self.output_keys:
            if key not in state:
                raise OutputValidationError(
                    f"Agent '{self.name}' failed to produce output: {key}"
                )
    
    def _create_response(
        self,
        content: Any,
        confidence: float = 1.0,
        processing_time_ms: Optional[float] = None,
        citations: Optional[list] = None,
        metadata: Optional[Dict] = None
    ) -> AgentResponse:
        """
        Create a standardized agent response envelope.
        
        Args:
            content: The primary response content
            confidence: Confidence score (0.0 - 1.0)
            processing_time_ms: Execution time in milliseconds
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
            processing_time_ms=processing_time_ms,
            citations=citations or [],
            metadata=metadata or {}
        )
    
    def _validate_model(self, data: Dict, model_class: Type[T]) -> T:
        """
        Validate data against a Pydantic model.
        
        Args:
            data: Dictionary to validate
            model_class: Pydantic model class
        
        Returns:
            Validated model instance
        
        Raises:
            OutputValidationError: If validation fails
        """
        try:
            return model_class(**data)
        except ValidationError as e:
            raise OutputValidationError(
                f"Agent '{self.name}' output validation failed: {e}"
            )
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"
