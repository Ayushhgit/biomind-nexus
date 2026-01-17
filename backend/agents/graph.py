"""
LangGraph Agent Orchestration - Drug Repurposing Workflow

Deterministic multi-agent workflow with MANDATORY simulation step.

Workflow (no bypasses for simulation or safety):
    Entity Extraction → Literature → Pathway Simulation → Reasoning → Ranking → Safety → Output

Architecture:
- Deterministic execution path (no free-form chat)
- Simulation ALWAYS runs (no bypass)
- Safety ALWAYS runs (no bypass)
- Agents do NOT access databases (data flows via state)
"""

from typing import Annotated, Literal
from langgraph.graph import StateGraph, END

from backend.agents.schemas import AgentState, DrugRepurposingQuery
from backend.agents.entity_extraction import EntityExtractionAgent
from backend.agents.literature import LiteratureAgent
from backend.agents.pathway_reasoning import PathwayReasoningAgent
from backend.agents.reasoning import ReasoningAgent
from backend.agents.ranking import RankingAgent
from backend.agents.safety import SafetyAgent


# =============================================================================
# Agent Instances
# =============================================================================

_entity_extraction_agent = EntityExtractionAgent()
_literature_agent = LiteratureAgent()
_pathway_reasoning_agent = PathwayReasoningAgent()
_reasoning_agent = ReasoningAgent()
_ranking_agent = RankingAgent()
_safety_agent = SafetyAgent()


# =============================================================================
# Node Functions
# =============================================================================

async def entity_extraction_node(state: AgentState) -> AgentState:
    """Extract biomedical entities from query."""
    return await _entity_extraction_agent.invoke(state)


async def literature_node(state: AgentState) -> AgentState:
    """Retrieve literature evidence for entities."""
    return await _literature_agent.invoke(state)


async def pathway_simulation_node(state: AgentState) -> AgentState:
    """Run deterministic pathway simulation."""
    return await _pathway_reasoning_agent.invoke(state)


async def reasoning_node(state: AgentState) -> AgentState:
    """Generate drug repurposing hypotheses."""
    return await _reasoning_agent.invoke(state)


async def ranking_node(state: AgentState) -> AgentState:
    """Rank and filter candidates."""
    return await _ranking_agent.invoke(state)


async def safety_node(state: AgentState) -> AgentState:
    """Final safety validation gate."""
    return await _safety_agent.invoke(state)


# =============================================================================
# Edge Conditions
# =============================================================================

def should_continue_to_ranking(state: AgentState) -> Literal["ranking", "safety"]:
    """Check if we have candidates to rank."""
    candidates = state.get("drug_candidates", [])
    return "ranking" if candidates else "safety"


# =============================================================================
# Graph Construction
# =============================================================================

def create_drug_repurposing_graph() -> StateGraph:
    """
    Construct the LangGraph for drug repurposing workflow.
    
    Graph Structure (MANDATORY simulation and safety):
    
        [START]
           │
           ▼
      Entity Extraction
           │
           ▼
       Literature
           │
           ▼
    Pathway Simulation  ◄── MANDATORY (no bypass)
           │
           ▼
       Reasoning
           │
           ▼
       (candidates?)
         ╱     ╲
        ▼       ▼
    Ranking  ──►  Safety  ◄── MANDATORY
        │           │
        └──────────►│
                    ▼
                  [END]
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("entity_extraction", entity_extraction_node)
    workflow.add_node("literature", literature_node)
    workflow.add_node("pathway_simulation", pathway_simulation_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("ranking", ranking_node)
    workflow.add_node("safety", safety_node)
    
    # Set entry point
    workflow.set_entry_point("entity_extraction")
    
    # Define edges - LINEAR until reasoning, then conditional
    workflow.add_edge("entity_extraction", "literature")
    workflow.add_edge("literature", "pathway_simulation")  # MANDATORY
    workflow.add_edge("pathway_simulation", "reasoning")   # MANDATORY
    
    # Reasoning -> Ranking OR Safety
    workflow.add_conditional_edges(
        "reasoning",
        should_continue_to_ranking,
        {
            "ranking": "ranking",
            "safety": "safety"
        }
    )
    
    # Ranking -> Safety (MANDATORY)
    workflow.add_edge("ranking", "safety")
    
    # Safety -> END
    workflow.add_edge("safety", END)
    
    return workflow.compile()


# Compiled graph instance
drug_repurposing_graph = create_drug_repurposing_graph()


# =============================================================================
# Entry Point
# =============================================================================

async def run_drug_repurposing_workflow(
    query: DrugRepurposingQuery,
    user_id: str,
    request_id: str
) -> AgentState:
    """
    Execute the drug repurposing workflow.
    
    Architecture:
        1. Pre-load graph data via DAL (agents never touch DB)
        2. Inject data into AgentState
        3. Run deterministic agent pipeline
        4. Log audit trail via DAL
    
    Args:
        query: Structured query input
        user_id: User identifier for audit
        request_id: Request identifier for tracing
    
    Returns:
        Final AgentState with all outputs
    """
    # Pre-load graph context via DAL (agents don't know about this)
    graph_context = await _preload_graph_context(query)
    
    initial_state: AgentState = {
        "query": query,
        "user_id": user_id,
        "request_id": request_id,
        "step_history": [],
        "errors": [],
        # Pre-loaded graph data (agents treat this as given)
        "graph_drug_targets": graph_context.get("drug_targets", []),
        "graph_disease_genes": graph_context.get("disease_genes", []),
        "graph_pathway_edges": graph_context.get("pathway_edges", []),
        "graph_neighbors": graph_context.get("neighbors", []),
    }
    
    final_state = await drug_repurposing_graph.ainvoke(initial_state)
    
    # Log workflow completion via DAL (agents don't know about this)
    await _log_workflow_completion(final_state, user_id, request_id)
    
    return final_state


async def _preload_graph_context(query: DrugRepurposingQuery) -> dict:
    """
    Pre-load and optionally INGEST graph data via DAL.
    
    1. Identify Drug/Disease from query
    2. Check if knowledge exists (via IngestionPipeline)
    3. If missing, Pipeline fetches papers & persists facts
    4. Return loaded graph context
    """
    try:
        # Lazy import ingestion to avoid circular deps/startup overhead
        from backend.ingestion.ingestion_pipeline import get_ingestion_pipeline
        
        # Extract drug/disease from query if pre-specified
        drug_name = query.source_drug.name if query.source_drug else None
        disease_name = query.target_disease.name if query.target_disease else None
        
        # If no pre-extracted entities, try parsing from raw query
        if not drug_name or not disease_name:
            # Simple heuristic extraction for ingestion trigger
            # (Real extraction happens in agents, this is just for pre-loading)
            import re
            text = query.raw_query.lower()
            
            # Very basic patterns just to trigger ingestion if obvious
            # In production, use a lightweight NER here
            # For now, rely on parsed query or skip ingestion if ambiguous
            pass

        if drug_name and disease_name:
            print(f"Orchestrator: Check ingestion for {drug_name} <-> {disease_name}")
            pipeline = get_ingestion_pipeline()
            # This handles Check -> Fetch? -> Persist? -> Load
            context = await pipeline.ingest_if_missing(drug_name, disease_name)
            return context
            
        print("Orchestrator: Insufficient entities for specific graph loading.")
        return {}
        
    except Exception as e:
        # Graceful degradation: agents can still work without graph data
        print(f"Graph context/ingestion skipped: {e}")
        return {}


async def _log_workflow_completion(
    state: AgentState,
    user_id: str,
    request_id: str
) -> None:
    """
    Log workflow completion via DAL.
    
    Called AFTER agents complete. Agents never access audit logging.
    """
    try:
        from backend.dal.cassandra_dal import log_workflow_complete
        
        await log_workflow_complete(
            request_id=request_id,
            user_id=user_id,
            approved=state.get("workflow_approved", False),
            step_history=state.get("step_history", []),
            total_candidates=len(state.get("final_candidates", []))
        )
    except Exception as e:
        # Graceful degradation: audit failure shouldn't break workflow
        print(f"Audit logging skipped: {e}")


# Legacy alias
agent_graph = drug_repurposing_graph

