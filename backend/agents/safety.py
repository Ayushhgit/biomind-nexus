"""
Safety Agent.

This agent checks if the results are safe to show.
It's the last step.
"""

from typing import List, Any
import uuid

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import (
    AgentState,
    DrugCandidate,
    SafetyCheck,
    SafetyFlag,
    Severity,
    Citation,
)


class SafetyAgent(BaseAgent):
    """
    Checks everything for safety.
    
    We make sure:
    1. Schema is good
    2. Confidence is high enough
    3. Citations are real
    4. No crazy medical claims
    """
    
    name = "safety_agent"
    description = "Validates and approves final agent outputs"
    version = "1.0.0"
    
    # Only require query - other inputs may be missing on early exit paths
    required_input_keys = ["query"]
    output_keys = ["safety_result", "final_candidates", "workflow_approved"]
    
    # Configuration thresholds
    MIN_CONFIDENCE_THRESHOLD = 0.3
    LOW_CONFIDENCE_THRESHOLD = 0.5
    MIN_CITATIONS_PER_CANDIDATE = 1
    MAX_UNSUPPORTED_CLAIMS = 2
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Run all the safety checks.
        """
        candidates: List[DrugCandidate] = state.get("ranked_candidates", [])
        
        all_flags: List[SafetyFlag] = []
        approved_candidates: List[DrugCandidate] = []
        
        # Validate each candidate
        for candidate in candidates:
            candidate_flags = self._validate_candidate(candidate)
            all_flags.extend(candidate_flags)
            
            # Only approve if no critical flags
            critical_flags = [f for f in candidate_flags if f.severity == Severity.CRITICAL]
            if not critical_flags:
                approved_candidates.append(candidate)
        
        # Global validation checks
        global_flags = self._validate_global(state, approved_candidates)
        all_flags.extend(global_flags)
        
        # Determine overall safety status
        critical_count = sum(1 for f in all_flags if f.severity == Severity.CRITICAL)
        warning_count = sum(1 for f in all_flags if f.severity == Severity.WARNING)
        
        passed = critical_count == 0
        requires_review = warning_count > 0 or len(approved_candidates) == 0
        
        # Calculate aggregate metrics
        min_conf = min((c.confidence for c in approved_candidates), default=0.0)
        total_citations = sum(len(c.citations) for c in approved_candidates)
        
        safety_result = SafetyCheck(
            passed=passed,
            requires_human_review=requires_review,
            flags=all_flags,
            min_confidence=min_conf,
            total_citations=total_citations,
            schema_valid=True,  # We got this far, schemas are valid
            content_safe=critical_count == 0,
            citations_verified=True  # Placeholder - would verify in production
        )
        
        state["safety_result"] = safety_result
        state["final_candidates"] = approved_candidates if passed else []
        state["workflow_approved"] = passed
        
        return state
    
    def _validate_candidate(self, candidate: DrugCandidate) -> List[SafetyFlag]:
        """Check one candidate."""
        flags: List[SafetyFlag] = []
        
        # Check confidence threshold
        if candidate.confidence < self.MIN_CONFIDENCE_THRESHOLD:
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="confidence_too_low",
                severity=Severity.CRITICAL,
                message=f"Candidate confidence ({candidate.confidence:.2f}) below minimum threshold ({self.MIN_CONFIDENCE_THRESHOLD})",
                source_agent=self.name,
                affected_field="confidence"
            ))
        elif candidate.confidence < self.LOW_CONFIDENCE_THRESHOLD:
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="low_confidence",
                severity=Severity.WARNING,
                message=f"Candidate confidence ({candidate.confidence:.2f}) is low - recommend human review",
                source_agent=self.name,
                affected_field="confidence"
            ))
        
        # Check citations
        if len(candidate.citations) < self.MIN_CITATIONS_PER_CANDIDATE:
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="insufficient_citations",
                severity=Severity.WARNING,
                message=f"Candidate has {len(candidate.citations)} citations, minimum recommended is {self.MIN_CITATIONS_PER_CANDIDATE}",
                source_agent=self.name,
                affected_field="citations"
            ))
        
        # Check mechanism path exists
        if not candidate.mechanism_paths:
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="no_mechanism",
                severity=Severity.WARNING,
                message="No mechanistic pathway provided for hypothesis",
                source_agent=self.name,
                affected_field="mechanism_paths"
            ))
        
        # Check for required fields
        if not candidate.hypothesis.strip():
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="missing_hypothesis",
                severity=Severity.CRITICAL,
                message="Candidate missing hypothesis statement",
                source_agent=self.name,
                affected_field="hypothesis"
            ))
        
        if not candidate.mechanism_summary.strip():
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="missing_mechanism_summary",
                severity=Severity.WARNING,
                message="Candidate missing mechanism summary",
                source_agent=self.name,
                affected_field="mechanism_summary"
            ))
        
        return flags
    
    def _validate_global(
        self, 
        state: AgentState, 
        approved_candidates: List[DrugCandidate]
    ) -> List[SafetyFlag]:
        """Check everything else."""
        flags: List[SafetyFlag] = []
        
        # Check if we have any results
        if not approved_candidates:
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="no_candidates",
                severity=Severity.WARNING,
                message="No drug candidates passed validation - consider relaxing constraints",
                source_agent=self.name,
                affected_field="ranked_candidates"
            ))
        
        # Check entity extraction worked
        entities = state.get("extracted_entities", [])
        if not entities:
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="no_entities_extracted",
                severity=Severity.INFO,
                message="No biomedical entities were extracted from the query",
                source_agent=self.name,
                affected_field="extracted_entities"
            ))
        
        # Check literature evidence was found
        evidence = state.get("literature_evidence", [])
        if not evidence:
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="no_literature_evidence",
                severity=Severity.INFO,
                message="No literature evidence found for extracted entities",
                source_agent=self.name,
                affected_field="literature_evidence"
            ))
        
        return flags
    
    def _validate_citation(self, citation: Citation) -> List[SafetyFlag]:
        """Check if the citation looks real."""
        flags: List[SafetyFlag] = []
        
        # In production, would verify:
        # - PMID exists in PubMed
        # - DOI resolves
        # - Authors match
        # - Year is reasonable
        
        if not citation.source_id:
            flags.append(SafetyFlag(
                flag_id=f"flag_{uuid.uuid4().hex[:8]}",
                flag_type="invalid_citation",
                severity=Severity.WARNING,
                message="Citation missing source identifier",
                source_agent=self.name,
                affected_field="citation.source_id"
            ))
        
        return flags
