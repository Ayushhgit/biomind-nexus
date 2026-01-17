"""
This is the base class for all our agents.
It makes sure every agent validates its input and output.

Rules:
- Agents are simple functions: input -> output
- Don't talk to the DB directly
- Don't handle auth here
- Outputs must be Pydantic models
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
    Base class for all agents.
    
    Every agent inherits from this. They have to implement `process`.
    
    How it works:
    1. invoke() is called
    2. We check inputs
    3. process() runs the logic
    4. We check outputs
    5. Return the new state
    
    Attributes:
        name: The agent's name
        description: What it does
        version: Version number
    """
    
    name: str = "base_agent"
    description: str = "Abstract base agent"
    version: str = "0.1.0"
    
    required_input_keys: list[str] = []
    output_keys: list[str] = []
    
    def __init__(self):
        """
        Initialize the agent.
        """
        pass
    
    async def invoke(self, state: AgentState) -> AgentState:
        """
        Run the agent function.
        
        This is what LangGraph calls.
        
        Args:
            state: The workflow state
        
        Returns:
            The new state
        
        Raises:
            InputValidationError: If something is missing
            OutputValidationError: If output is bad
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
        Run the main logic.
        You MUST override this function.
        
        Args:
            state: The current state
        
        Returns:
            The new state
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
        Check if we have the right outputs.
        
        Raises:
            OutputValidationError: If check fails
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
