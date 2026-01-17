"""
BioMind Nexus - Safety Agent

Guardrail agent that validates all outputs before returning to user.
Acts as the final checkpoint in the agent pipeline.

Responsibilities:
- Validate response format against schemas
- Check for harmful or misleading content
- Ensure citations are properly attributed
- Flag low-confidence responses for human review

Security: This agent is MANDATORY in all execution paths.
"""

from typing import List, Dict, Any

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import AgentState, SafetyCheck, SafetyFlag


class SafetyAgent(BaseAgent):
    """
    Guardrail agent for output validation and safety checks.
    
    All agent responses MUST pass through this agent before
    being returned to the user.
    
    Checks performed:
    1. Schema validation (response structure)
    2. Content safety (no harmful claims)
    3. Citation validation (sources exist)
    4. Confidence thresholds (flag uncertain responses)
    """
    
    name = "safety_agent"
    description = "Validates and sanitizes agent outputs"
    version = "0.1.0"
    
    # Confidence threshold below which responses are flagged
    CONFIDENCE_THRESHOLD = 0.5
    
    def _initialize_services(self):
        """Initialize safety checking services."""
        # TODO: Initialize content safety classifier
        # TODO: Initialize citation validator
        pass
    
    async def invoke(self, state: AgentState) -> AgentState:
        """
        Validate agent responses and apply safety checks.
        
        Args:
            state: Contains responses from previous agents
        
        Returns:
            State updated with 'safety_result' containing
            validation status and any flags raised
        """
        safety_flags: List[SafetyFlag] = []
        
        # Check all response types
        for response_key in ["literature_response", "reasoning_response"]:
            if response_key in state:
                flags = await self._validate_response(state[response_key])
                safety_flags.extend(flags)
        
        # Determine overall safety status
        is_safe = all(flag.severity != "critical" for flag in safety_flags)
        requires_review = any(flag.severity == "warning" for flag in safety_flags)
        
        safety_result = SafetyCheck(
            passed=is_safe,
            requires_human_review=requires_review,
            flags=safety_flags,
        )
        
        state["safety_result"] = safety_result
        state["final_response_approved"] = is_safe
        
        return state
    
    async def _validate_response(self, response: Any) -> List[SafetyFlag]:
        """
        Run validation checks on a single agent response.
        
        Returns:
            List of safety flags (empty if no issues)
        """
        flags = []
        
        # Check confidence threshold
        confidence = getattr(response, "confidence", 1.0)
        if confidence < self.CONFIDENCE_THRESHOLD:
            flags.append(SafetyFlag(
                type="low_confidence",
                severity="warning",
                message=f"Response confidence ({confidence:.2f}) below threshold"
            ))
        
        # TODO: Add content safety check
        # TODO: Add citation validation
        # TODO: Add schema validation
        
        return flags
    
    async def _check_content_safety(self, content: str) -> List[SafetyFlag]:
        """
        Check content for harmful or misleading claims.
        
        Categories checked:
        - Medical misinformation
        - Unsubstantiated claims
        - Dangerous recommendations
        
        Returns:
            List of safety flags
        """
        # TODO: Implement content classifier
        return []
    
    async def _validate_citations(self, citations: List[Dict]) -> List[SafetyFlag]:
        """
        Validate that all citations reference real sources.
        
        Returns:
            Flags for invalid or suspicious citations
        """
        # TODO: Implement citation checker
        return []
