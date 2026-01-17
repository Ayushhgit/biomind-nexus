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
    
    Args:
        query: Structured query input
        user_id: User identifier for audit
        request_id: Request identifier for tracing
    
    Returns:
        Final AgentState with all outputs
    """
    initial_state: AgentState = {
        "query": query,
        "user_id": user_id,
        "request_id": request_id,
        "step_history": [],
        "errors": [],
    }
    
    final_state = await drug_repurposing_graph.ainvoke(initial_state)
    
    return final_state


# Legacy alias
agent_graph = drug_repurposing_graph
