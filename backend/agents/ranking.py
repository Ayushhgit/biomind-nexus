"""
BioMind Nexus - Ranking Agent

Final ranking and scoring of drug repurposing candidates.
Applies weighted multi-criteria ranking algorithm.

Responsibilities:
- Aggregate scores from multiple dimensions
- Apply configurable weights for ranking
- Enforce query constraints (min_confidence, max_candidates)
- Return final ordered list of candidates

Design: Pure function - receives candidates, returns ranked list.
"""

from typing import List
from dataclasses import dataclass

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import (
    AgentState,
    DrugCandidate,
    DrugRepurposingQuery,
)


@dataclass(frozen=True)
class RankingWeights:
    """Configurable weights for multi-criteria ranking."""
    overall_score: float = 0.35
    confidence: float = 0.25
    evidence_count: float = 0.20
    mechanism_paths: float = 0.15
    novelty: float = 0.05
    
    def validate(self) -> bool:
        total = (
            self.overall_score + 
            self.confidence + 
            self.evidence_count + 
            self.mechanism_paths + 
            self.novelty
        )
        return abs(total - 1.0) < 0.001


class RankingAgent(BaseAgent):
    """
    Agent for final candidate ranking and filtering.
    
    Applies a weighted scoring algorithm to produce the final
    ranked list of drug repurposing candidates.
    
    Pure Input: drug_candidates, query constraints
    Pure Output: ranked_candidates
    """
    
    name = "ranking_agent"
    description = "Ranks and filters drug repurposing candidates"
    version = "1.0.0"
    
    required_input_keys = ["query", "drug_candidates"]
    output_keys = ["ranked_candidates"]
    
    # Default ranking weights
    DEFAULT_WEIGHTS = RankingWeights()
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Rank and filter drug candidates.
        
        Args:
            state: Contains drug_candidates from ReasoningAgent
        
        Returns:
            State with ranked_candidates list
        """
        query: DrugRepurposingQuery = state["query"]
        candidates: List[DrugCandidate] = state.get("drug_candidates", [])
        
        if not candidates:
            state["ranked_candidates"] = []
            return state
        
        # Calculate composite scores
        scored_candidates = []
        for candidate in candidates:
            composite_score = self._calculate_composite_score(candidate)
            scored_candidates.append((composite_score, candidate))
        
        # Sort by composite score (descending)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Apply filters from query
        filtered_candidates = []
        for score, candidate in scored_candidates:
            # Apply min_confidence filter
            if candidate.confidence < query.min_confidence:
                continue
            
            # Update candidate with final rank
            candidate.rank = len(filtered_candidates) + 1
            filtered_candidates.append(candidate)
            
            # Apply max_candidates limit
            if len(filtered_candidates) >= query.max_candidates:
                break
        
        state["ranked_candidates"] = filtered_candidates
        
        return state
    
    def _calculate_composite_score(self, candidate: DrugCandidate) -> float:
        """
        Calculate weighted composite score for ranking.
        
        Scoring dimensions:
        - overall_score: Base score from reasoning
        - confidence: Mechanism confidence
        - evidence_count: Number of supporting evidence items
        - mechanism_paths: Number of mechanistic pathways
        - novelty: Novelty score (higher = more novel)
        """
        weights = self.DEFAULT_WEIGHTS
        
        # Normalize evidence count (assume max 20 for normalization)
        evidence_normalized = min(candidate.evidence_count / 20.0, 1.0)
        
        # Normalize mechanism paths (assume max 5)
        paths_normalized = min(len(candidate.mechanism_paths) / 5.0, 1.0)
        
        composite = (
            weights.overall_score * candidate.overall_score +
            weights.confidence * candidate.confidence +
            weights.evidence_count * evidence_normalized +
            weights.mechanism_paths * paths_normalized +
            weights.novelty * candidate.novelty_score
        )
        
        return composite
