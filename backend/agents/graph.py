"""
BioMind Nexus - LangGraph Agent Orchestration

Defines the agent execution graph using LangGraph.
This is the central orchestration layer that routes queries to specialized agents.

Architecture:
- Agents are nodes in a directed graph
- Edges define conditional routing based on query type
- All agent outputs are validated against schemas before returning

Security: Agents do NOT have direct database access.
All data retrieval goes through typed service layers.
"""

from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END

from backend.agents.base_agent import BaseAgent
from backend.agents.literature import LiteratureAgent
from backend.agents.reasoning import ReasoningAgent
from backend.agents.safety import SafetyAgent
from backend.agents.schemas import AgentState, QueryType


def create_agent_graph() -> StateGraph:
    """
    Construct the LangGraph execution graph for agent orchestration.
    
    Graph Structure:
        [START] -> router -> literature_agent -> safety_check -> [END]
                          -> reasoning_agent  -> safety_check -> [END]
    
    All paths pass through safety_check before returning results.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    
    # Initialize agents
    literature = LiteratureAgent()
    reasoning = ReasoningAgent()
    safety = SafetyAgent()
    
    # Define the graph
    graph = StateGraph(AgentState)
    
    # Add nodes (agent execution steps)
    graph.add_node("router", route_query)
    graph.add_node("literature_agent", literature.invoke)
    graph.add_node("reasoning_agent", reasoning.invoke)
    graph.add_node("safety_check", safety.invoke)
    
    # Define edges
    graph.set_entry_point("router")
    
    # Conditional routing based on query type
    graph.add_conditional_edges(
        "router",
        determine_agent,
        {
            QueryType.LITERATURE: "literature_agent",
            QueryType.REASONING: "reasoning_agent",
        }
    )
    
    # All agents route to safety check
    graph.add_edge("literature_agent", "safety_check")
    graph.add_edge("reasoning_agent", "safety_check")
    
    # Safety check ends the graph
    graph.add_edge("safety_check", END)
    
    return graph.compile()


def route_query(state: AgentState) -> AgentState:
    """
    Initial routing node that classifies the incoming query.
    
    Updates state with determined query_type for conditional routing.
    """
    # TODO: Implement query classification logic
    # For now, default to literature search
    state["query_type"] = QueryType.LITERATURE
    return state


def determine_agent(state: AgentState) -> QueryType:
    """
    Edge condition function for routing to appropriate agent.
    
    Returns the query_type to select the correct branch.
    """
    return state.get("query_type", QueryType.LITERATURE)


# Compiled graph instance for import
agent_graph = create_agent_graph()
