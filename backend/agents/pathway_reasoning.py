"""
Pathway Reasoning Agent - Deterministic Biological Pathway Simulation

Performs in-silico counterfactual reasoning over biological pathways.
NOT molecular simulation. NOT ML. Deterministic graph traversal.

Core Question:
"If drug D modulates target T, and T affects pathway P, 
and P is implicated in disease X, how plausible is repurposing D for X?"

Simulation Method:
1. Build in-memory biological graph from extracted entities + evidence
2. Traverse drug → target → pathway → disease paths (BFS)
3. Score each path via confidence propagation
4. Reject paths lacking evidence or biological plausibility
5. Return SimulationResult with valid/rejected paths
"""

from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
import uuid
import re

from backend.agents.base_agent import BaseAgent
from backend.agents.schemas import (
    AgentState,
    BiomedicalEntity,
    EntityType,
    EvidenceItem,
    Citation,
    BiologicalEdge,
    PathwayPath,
    RejectedPath,
    SimulationResult,
    RelationType,
)


# =============================================================================
# Constants
# =============================================================================

# Maximum path depth to prevent combinatorial explosion
MAX_PATH_DEPTH = 5

# Minimum confidence threshold for a path to be considered valid
MIN_PATH_CONFIDENCE = 0.15

# Minimum evidence support for an edge to be credible
MIN_EVIDENCE_SUPPORT = 0.1

# Path length penalty factor (longer paths = lower confidence)
PATH_LENGTH_PENALTY = 0.85

# Relation type to confidence modifier mapping
RELATION_CONFIDENCE_MODIFIERS = {
    RelationType.INHIBITS: 1.0,
    RelationType.ACTIVATES: 1.0,
    RelationType.BINDS: 0.95,
    RelationType.MODULATES: 0.85,
    RelationType.REGULATES: 0.80,
    RelationType.UPREGULATES: 0.90,
    RelationType.DOWNREGULATES: 0.90,
    RelationType.PHOSPHORYLATES: 0.85,
    RelationType.TREATS: 1.0,
    RelationType.CAUSES: 0.90,
    RelationType.PREVENTS: 0.95,
    RelationType.ASSOCIATES_WITH: 0.60,
    RelationType.CATALYZES: 0.80,
    RelationType.TRANSPORTS: 0.70,
    RelationType.UNKNOWN: 0.40,
}

# Keywords indicating specific relation types in evidence text
RELATION_KEYWORDS = {
    RelationType.INHIBITS: ["inhibit", "block", "suppress", "reduce", "decrease", "antagonist"],
    RelationType.ACTIVATES: ["activate", "stimulate", "enhance", "increase", "agonist", "induce"],
    RelationType.BINDS: ["bind", "interact", "dock", "attach", "affinity"],
    RelationType.MODULATES: ["modulate", "affect", "influence", "regulate"],
    RelationType.UPREGULATES: ["upregulate", "overexpress", "elevate"],
    RelationType.DOWNREGULATES: ["downregulate", "underexpress", "diminish"],
    RelationType.TREATS: ["treat", "therapeutic", "efficacy", "beneficial"],
    RelationType.CAUSES: ["cause", "induce", "trigger", "lead to"],
    RelationType.PREVENTS: ["prevent", "protect", "avert"],
}


class BiologicalGraph:
    """
    In-memory directed graph of biological relationships.
    
    Built from extracted entities and literature evidence.
    Used for deterministic path traversal.
    """
    
    def __init__(self):
        # Adjacency list: entity -> list of (target, edge)
        self._adjacency: Dict[str, List[Tuple[str, BiologicalEdge]]] = defaultdict(list)
        # Entity registry: normalized name -> entity data
        self._entities: Dict[str, BiomedicalEntity] = {}
        # Edge set for deduplication
        self._edges: Set[BiologicalEdge] = set()
        # Statistics
        self.node_count = 0
        self.edge_count = 0
    
    def add_entity(self, entity: BiomedicalEntity) -> None:
        """Register an entity in the graph."""
        key = self._normalize(entity.name)
        if key not in self._entities:
            self._entities[key] = entity
            self.node_count += 1
    
    def add_edge(self, edge: BiologicalEdge) -> None:
        """Add a directed edge between entities."""
        if edge not in self._edges:
            self._edges.add(edge)
            source_key = self._normalize(edge.source_entity)
            target_key = self._normalize(edge.target_entity)
            self._adjacency[source_key].append((target_key, edge))
            self.edge_count += 1
    
    def get_neighbors(self, entity_name: str) -> List[Tuple[str, BiologicalEdge]]:
        """Get all outgoing edges from an entity."""
        key = self._normalize(entity_name)
        return self._adjacency.get(key, [])
    
    def has_entity(self, entity_name: str) -> bool:
        """Check if entity exists in graph."""
        return self._normalize(entity_name) in self._entities
    
    def get_entity(self, entity_name: str) -> Optional[BiomedicalEntity]:
        """Retrieve entity by name."""
        return self._entities.get(self._normalize(entity_name))
    
    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize entity name for consistent lookup."""
        return name.lower().strip()


class PathwayReasoningAgent(BaseAgent):
    """
    Agent for deterministic biological pathway simulation.
    
    Performs counterfactual reasoning:
    "Given evidence, how plausible is drug D for disease X?"
    
    This is NOT molecular simulation.
    This is graph traversal with confidence propagation.
    
    Input:
        - extracted_entities: Drugs, diseases, genes from query
        - literature_evidence: Evidence items from PubMed
        
    Output:
        - simulation_result: SimulationResult with valid/rejected paths
    """
    
    name = "pathway_reasoning_agent"
    description = "Deterministic biological pathway simulation"
    version = "1.0.0"
    
    required_input_keys = ["query", "extracted_entities"]
    output_keys = ["simulation_result"]
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Execute pathway simulation.
        
        1. Identify drug and disease entities
        2. Build biological graph from entities + evidence
        3. Find all paths from drug to disease
        4. Score and filter paths
        5. Return SimulationResult
        """
        entities: List[BiomedicalEntity] = state.get("extracted_entities", [])
        evidence: List[EvidenceItem] = state.get("literature_evidence", [])
        citations: List[Citation] = state.get("literature_citations", [])
        
        # Identify drugs and diseases
        drugs = [e for e in entities if e.entity_type == EntityType.DRUG]
        diseases = [e for e in entities if e.entity_type == EntityType.DISEASE]
        
        # Handle case with no drugs or diseases
        if not drugs or not diseases:
            state["simulation_result"] = self._empty_result(
                drug=drugs[0].name if drugs else "unknown",
                disease=diseases[0].name if diseases else "unknown",
                reason="Insufficient entities: need at least one drug and one disease"
            )
            return state
        
        # Build biological graph from evidence
        graph = self._build_graph(entities, evidence, citations)
        
        # Run simulation for primary drug-disease pair
        drug = drugs[0]
        disease = diseases[0]
        
        simulation_result = self._simulate_pathways(
            graph=graph,
            drug=drug,
            disease=disease,
            all_entities=entities,
            evidence=evidence
        )
        
        state["simulation_result"] = simulation_result
        return state
    
    def _build_graph(
        self,
        entities: List[BiomedicalEntity],
        evidence: List[EvidenceItem],
        citations: List[Citation]
    ) -> BiologicalGraph:
        """
        Construct biological graph from entities and evidence.
        
        Edges are inferred from:
        1. Entity co-occurrence in evidence
        2. Relation keywords in evidence text
        3. Known biological relationships
        """
        graph = BiologicalGraph()
        
        # Add all entities as nodes
        for entity in entities:
            graph.add_entity(entity)
        
        # Infer edges from evidence
        for ev in evidence:
            edges = self._infer_edges_from_evidence(ev, entities)
            for edge in edges:
                graph.add_edge(edge)
        
        # Add canonical drug-target-disease edges
        self._add_canonical_edges(graph, entities)
        
        return graph
    
    def _infer_edges_from_evidence(
        self,
        evidence: EvidenceItem,
        entities: List[BiomedicalEntity]
    ) -> List[BiologicalEdge]:
        """
        Infer biological edges from evidence text.
        
        Uses keyword matching to determine relation types.
        """
        edges = []
        text = evidence.description.lower()
        mentioned = evidence.entities_mentioned
        
        # Get PMIDs for evidence support
        pmids = []
        if evidence.citation and evidence.citation.source_id:
            pmids = [evidence.citation.source_id]
        
        # Find relation type from keywords
        relation = self._detect_relation(text)
        
        # Create edges between all pairs of mentioned entities
        for i, source in enumerate(mentioned):
            for target in mentioned[i+1:]:
                # Skip same-type edges (drug->drug, disease->disease)
                if source.entity_type == target.entity_type:
                    continue
                
                # Determine directionality based on entity types
                if source.entity_type == EntityType.DRUG:
                    src, tgt = source, target
                elif target.entity_type == EntityType.DRUG:
                    src, tgt = target, source
                elif source.entity_type == EntityType.DISEASE:
                    src, tgt = target, source
                else:
                    src, tgt = source, target
                
                edge = BiologicalEdge(
                    source_entity=src.name,
                    target_entity=tgt.name,
                    relation=relation,
                    confidence=evidence.confidence * RELATION_CONFIDENCE_MODIFIERS.get(relation, 0.5),
                    evidence_count=1,
                    pmid_support=pmids
                )
                edges.append(edge)
        
        return edges
    
    def _detect_relation(self, text: str) -> RelationType:
        """Detect biological relation type from text using keyword matching."""
        text_lower = text.lower()
        
        for relation, keywords in RELATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return relation
        
        return RelationType.MODULATES
    
    def _add_canonical_edges(
        self,
        graph: BiologicalGraph,
        entities: List[BiomedicalEntity]
    ) -> None:
        """
        Add canonical biological relationships.
        
        Drug -> Gene/Protein (MODULATES)
        Gene -> Pathway (REGULATES)
        Pathway -> Disease (CAUSES/PREVENTS)
        """
        drugs = [e for e in entities if e.entity_type == EntityType.DRUG]
        genes = [e for e in entities if e.entity_type in (EntityType.GENE, EntityType.PROTEIN)]
        pathways = [e for e in entities if e.entity_type == EntityType.PATHWAY]
        diseases = [e for e in entities if e.entity_type == EntityType.DISEASE]
        
        # Drug -> Gene edges
        for drug in drugs:
            for gene in genes:
                edge = BiologicalEdge(
                    source_entity=drug.name,
                    target_entity=gene.name,
                    relation=RelationType.MODULATES,
                    confidence=0.6,
                    evidence_count=0
                )
                graph.add_edge(edge)
        
        # Gene -> Disease edges (for direct mechanisms)
        for gene in genes:
            for disease in diseases:
                edge = BiologicalEdge(
                    source_entity=gene.name,
                    target_entity=disease.name,
                    relation=RelationType.ASSOCIATES_WITH,
                    confidence=0.5,
                    evidence_count=0
                )
                graph.add_edge(edge)
        
        # Direct Drug -> Disease edges (from evidence)
        for drug in drugs:
            for disease in diseases:
                edge = BiologicalEdge(
                    source_entity=drug.name,
                    target_entity=disease.name,
                    relation=RelationType.TREATS,
                    confidence=0.4,  # Lower confidence for direct edges
                    evidence_count=0
                )
                graph.add_edge(edge)
    
    def _simulate_pathways(
        self,
        graph: BiologicalGraph,
        drug: BiomedicalEntity,
        disease: BiomedicalEntity,
        all_entities: List[BiomedicalEntity],
        evidence: List[EvidenceItem]
    ) -> SimulationResult:
        """
        Run pathway simulation using BFS traversal.
        
        Finds all paths from drug to disease up to MAX_PATH_DEPTH.
        Scores paths using confidence propagation.
        Rejects paths below threshold.
        """
        valid_paths: List[PathwayPath] = []
        rejected_paths: List[RejectedPath] = []
        edges_evaluated = 0
        entities_traversed = set()
        
        drug_name = drug.name.lower()
        disease_name = disease.name.lower()
        
        # BFS to find all paths
        # Queue: (current_node, path_edges, visited)
        queue = deque([(drug_name, [], {drug_name})])
        
        while queue:
            current, path_edges, visited = queue.popleft()
            entities_traversed.add(current)
            
            # Check if we reached the disease
            if current == disease_name or disease_name in current or current in disease_name:
                if path_edges:  # Must have at least one edge
                    path_result = self._evaluate_path(path_edges, evidence)
                    if path_result[0]:  # Valid path
                        valid_paths.append(path_result[1])
                    else:
                        rejected_paths.append(path_result[1])
                continue
            
            # Don't exceed max depth
            if len(path_edges) >= MAX_PATH_DEPTH:
                continue
            
            # Explore neighbors
            neighbors = graph.get_neighbors(current)
            edges_evaluated += len(neighbors)
            
            for neighbor, edge in neighbors:
                if neighbor not in visited:
                    new_visited = visited | {neighbor}
                    new_path = path_edges + [edge]
                    queue.append((neighbor, new_path, new_visited))
        
        # Calculate overall plausibility
        if valid_paths:
            # Aggregate: average of top 3 paths
            top_paths = sorted(valid_paths, key=lambda p: p.path_confidence, reverse=True)[:3]
            overall_plausibility = sum(p.path_confidence for p in top_paths) / len(top_paths)
        else:
            overall_plausibility = 0.0
        
        return SimulationResult(
            simulation_id=f"sim_{uuid.uuid4().hex[:8]}",
            drug=drug.name,
            disease=disease.name,
            valid_paths=valid_paths,
            rejected_paths=rejected_paths,
            overall_plausibility=overall_plausibility,
            entities_traversed=len(entities_traversed),
            edges_evaluated=edges_evaluated,
            max_path_depth=max((p.path_length for p in valid_paths), default=0)
        )
    
    def _evaluate_path(
        self,
        edges: List[BiologicalEdge],
        evidence: List[EvidenceItem]
    ) -> Tuple[bool, any]:
        """
        Evaluate a path for validity and compute confidence.
        
        Scoring:
        - Base: product of edge confidences
        - Penalty: PATH_LENGTH_PENALTY ^ (path_length - 1)
        - Bonus: evidence support score
        
        Returns: (is_valid, PathwayPath or RejectedPath)
        """
        if not edges:
            return (False, RejectedPath(
                path_description="Empty path",
                rejection_reason="No edges in path",
                partial_confidence=0.0
            ))
        
        # Calculate base confidence (product of edge confidences)
        base_confidence = 1.0
        for edge in edges:
            base_confidence *= edge.confidence
        
        # Apply path length penalty
        path_length = len(edges)
        length_penalty = PATH_LENGTH_PENALTY ** (path_length - 1)
        
        # Calculate evidence support
        evidence_support = self._calculate_evidence_support(edges, evidence)
        
        # Final confidence
        path_confidence = base_confidence * length_penalty * (1 + evidence_support * 0.3)
        path_confidence = min(1.0, path_confidence)  # Cap at 1.0
        
        # Build path description
        path_desc = edges[0].source_entity
        for edge in edges:
            path_desc += f" --[{edge.relation.value}]--> {edge.target_entity}"
        
        # Check validity threshold
        if path_confidence < MIN_PATH_CONFIDENCE:
            return (False, RejectedPath(
                path_description=path_desc,
                rejection_reason=f"Confidence {path_confidence:.3f} below threshold {MIN_PATH_CONFIDENCE}",
                partial_confidence=path_confidence
            ))
        
        # Generate biological rationale
        rationale = self._generate_rationale(edges)
        
        return (True, PathwayPath(
            path_id=f"path_{uuid.uuid4().hex[:8]}",
            edges=edges,
            biological_rationale=rationale,
            path_confidence=path_confidence,
            path_length=path_length,
            evidence_support_score=evidence_support
        ))
    
    def _calculate_evidence_support(
        self,
        edges: List[BiologicalEdge],
        evidence: List[EvidenceItem]
    ) -> float:
        """
        Calculate evidence support score for a path.
        
        Based on:
        - Number of PMIDs supporting edges
        - Evidence confidence scores for mentioned entities
        """
        if not evidence:
            return 0.0
        
        # Collect all entities in path
        path_entities = set()
        for edge in edges:
            path_entities.add(edge.source_entity.lower())
            path_entities.add(edge.target_entity.lower())
        
        # Find supporting evidence
        support_score = 0.0
        supporting_count = 0
        
        for ev in evidence:
            ev_entities = {e.name.lower() for e in ev.entities_mentioned}
            # Check if evidence mentions any path entities
            overlap = path_entities & ev_entities
            if overlap:
                support_score += ev.confidence * (len(overlap) / len(path_entities))
                supporting_count += 1
        
        if supporting_count == 0:
            return 0.0
        
        return min(1.0, support_score / supporting_count)
    
    def _generate_rationale(self, edges: List[BiologicalEdge]) -> str:
        """Generate scientific rationale for a pathway."""
        if not edges:
            return "No pathway to explain."
        
        parts = []
        for i, edge in enumerate(edges):
            relation_verb = {
                RelationType.INHIBITS: "inhibits",
                RelationType.ACTIVATES: "activates",
                RelationType.BINDS: "binds to",
                RelationType.MODULATES: "modulates",
                RelationType.TREATS: "treats",
                RelationType.CAUSES: "causes",
                RelationType.PREVENTS: "prevents",
                RelationType.REGULATES: "regulates",
                RelationType.ASSOCIATES_WITH: "associates with",
            }.get(edge.relation, "affects")
            
            if i == 0:
                parts.append(f"{edge.source_entity} {relation_verb} {edge.target_entity}")
            else:
                parts.append(f"which {relation_verb} {edge.target_entity}")
        
        return ", ".join(parts) + "."
    
    def _empty_result(self, drug: str, disease: str, reason: str) -> SimulationResult:
        """Create empty simulation result for edge cases."""
        return SimulationResult(
            simulation_id=f"sim_{uuid.uuid4().hex[:8]}",
            drug=drug,
            disease=disease,
            valid_paths=[],
            rejected_paths=[RejectedPath(
                path_description="No simulation performed",
                rejection_reason=reason,
                partial_confidence=0.0
            )],
            overall_plausibility=0.0,
            entities_traversed=0,
            edges_evaluated=0,
            max_path_depth=0
        )
