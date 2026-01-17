"""
Reasoning Agent - Hypothesis Generation

Consumes SimulationResult from PathwayReasoningAgent.
Generates structured DrugCandidate outputs using LLM.

Does NOT perform pathway logic itself - that is done by PathwayReasoningAgent.
This agent synthesizes simulation results into human-readable hypotheses.
"""

from typing import List, Dict, Any
import uuid
from datetime import datetime

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import (
    AgentState,
    BiomedicalEntity,
    EntityType,
    EvidenceItem,
    MechanismPath,
    DrugCandidate,
    Citation,
    SimulationResult,
    PathwayPath,
)
from backend.services.llm_service import (
    generate_hypothesis_with_llm,
)


class ReasoningAgent(BaseAgent):
    """
    Hypothesis generation agent.
    
    Consumes:
        - simulation_result: PathwayPath data from simulation
        - extracted_entities: Drug/disease entities
        - literature_evidence: Supporting citations
    
    Produces:
        - drug_candidates: List of structured hypotheses
        - mechanism_paths: List of MechanismPath objects
    """
    
    name = "reasoning_agent"
    description = "Generates drug repurposing hypotheses from simulation results"
    version = "3.0.0"
    
    required_input_keys = ["query", "extracted_entities"]
    output_keys = ["mechanism_paths", "drug_candidates"]
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Generate hypotheses from simulation results.
        """
        entities: List[BiomedicalEntity] = state.get("extracted_entities", [])
        evidence: List[EvidenceItem] = state.get("literature_evidence", [])
        citations: List[Citation] = state.get("literature_citations", [])
        simulation: SimulationResult = state.get("simulation_result")
        
        drugs = [e for e in entities if e.entity_type == EntityType.DRUG]
        diseases = [e for e in entities if e.entity_type == EntityType.DISEASE]
        
        mechanism_paths: List[MechanismPath] = []
        drug_candidates: List[DrugCandidate] = []
        
        # Handle case with no simulation or no valid paths
        if not simulation or not simulation.has_valid_paths:
            if drugs and diseases:
                # Generate fallback hypothesis without simulation
                candidate = await self._generate_fallback_candidate(
                    drug=drugs[0],
                    disease=diseases[0],
                    evidence=evidence,
                    citations=citations
                )
                if candidate:
                    drug_candidates.append(candidate)
        else:
            # Generate hypotheses from simulation paths
            for path in simulation.valid_paths:
                mechanism = self._pathway_to_mechanism(path, entities)
                if mechanism:
                    mechanism_paths.append(mechanism)
            
            # Generate candidates for drug-disease pair
            if drugs and diseases:
                candidate = await self._generate_candidate_from_simulation(
                    drug=drugs[0],
                    disease=diseases[0],
                    simulation=simulation,
                    mechanism_paths=mechanism_paths,
                    evidence=evidence,
                    citations=citations
                )
                if candidate:
                    drug_candidates.append(candidate)
        
        state["mechanism_paths"] = mechanism_paths
        state["drug_candidates"] = drug_candidates
        
        return state
    
    def _pathway_to_mechanism(
        self,
        path: PathwayPath,
        entities: List[BiomedicalEntity]
    ) -> MechanismPath:
        """Convert PathwayPath to MechanismPath schema."""
        # Build entity nodes
        nodes = []
        entity_lookup = {e.name.lower(): e for e in entities}
        
        if path.edges:
            # Add source of first edge
            source_name = path.edges[0].source_entity
            source_entity = entity_lookup.get(source_name.lower())
            if source_entity:
                nodes.append(source_entity)
            else:
                nodes.append(BiomedicalEntity(
                    id=f"inferred:{source_name.lower()}",
                    name=source_name,
                    entity_type=EntityType.PATHWAY
                ))
            
            # Add targets of each edge
            for edge in path.edges:
                target_name = edge.target_entity
                target_entity = entity_lookup.get(target_name.lower())
                if target_entity:
                    nodes.append(target_entity)
                else:
                    nodes.append(BiomedicalEntity(
                        id=f"inferred:{target_name.lower()}",
                        name=target_name,
                        entity_type=EntityType.PATHWAY
                    ))
        
        edge_types = [e.relation.value for e in path.edges]
        
        return MechanismPath(
            path_id=path.path_id,
            nodes=nodes,
            edge_types=edge_types,
            confidence=path.path_confidence,
            supporting_citations=[]
        )
    
    async def _generate_candidate_from_simulation(
        self,
        drug: BiomedicalEntity,
        disease: BiomedicalEntity,
        simulation: SimulationResult,
        mechanism_paths: List[MechanismPath],
        evidence: List[EvidenceItem],
        citations: List[Citation]
    ) -> DrugCandidate:
        """Generate DrugCandidate from simulation results."""
        
        # Collect evidence summaries
        evidence_summaries = [e.description[:200] for e in evidence[:5]]
        
        # Add simulation path summaries
        for path in simulation.valid_paths[:3]:
            evidence_summaries.append(path.biological_rationale)
        
        # Generate hypothesis using LLM
        hypothesis_result = await generate_hypothesis_with_llm(
            drug=drug.name,
            disease=disease.name,
            evidence_summaries=evidence_summaries
        )
        
        # Calculate overall score from simulation + evidence
        sim_score = simulation.overall_plausibility
        evidence_score = len(evidence) / 20.0  # Normalize
        overall_score = (sim_score * 0.6) + (min(evidence_score, 0.4))
        
        return DrugCandidate(
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            drug=drug,
            target_disease=disease,
            hypothesis=hypothesis_result.get("hypothesis", f"{drug.name} may treat {disease.name}."),
            mechanism_summary=hypothesis_result.get("mechanism_summary", simulation.top_path.biological_rationale if simulation.top_path else ""),
            overall_score=min(1.0, overall_score),
            confidence=hypothesis_result.get("confidence", sim_score),
            novelty_score=0.6,
            mechanism_paths=mechanism_paths[:3],
            evidence_items=evidence[:5],
            citations=citations[:5]
        )
    
    async def _generate_fallback_candidate(
        self,
        drug: BiomedicalEntity,
        disease: BiomedicalEntity,
        evidence: List[EvidenceItem],
        citations: List[Citation]
    ) -> DrugCandidate:
        """Generate candidate when no simulation paths available."""
        
        evidence_summaries = [e.description[:200] for e in evidence[:5]]
        
        hypothesis_result = await generate_hypothesis_with_llm(
            drug=drug.name,
            disease=disease.name,
            evidence_summaries=evidence_summaries
        )
        
        return DrugCandidate(
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            drug=drug,
            target_disease=disease,
            hypothesis=hypothesis_result.get("hypothesis", f"{drug.name} may have potential for {disease.name}."),
            mechanism_summary=hypothesis_result.get("mechanism_summary", "Mechanism requires further investigation."),
            overall_score=0.3,  # Lower score without simulation support
            confidence=hypothesis_result.get("confidence", 0.3),
            novelty_score=0.5,
            mechanism_paths=[],
            evidence_items=evidence[:5],
            citations=citations[:5]
        )
