from __future__ import annotations

from langgraph.graph import StateGraph, START, END  # type: ignore

from .state_types import TopologyState
from .ingress_node import ingress_node
from .planner_node import planner_node
from .tool_node import tool_node
from .correlate_validate_node import correlate_and_validate_node
from .response_node import response_node
from .routers import refinement_router


def build_workflow():
    """
    Build and compile the LangGraph workflow for the topology agent.

    Current structure:

        START
          ↓
        ingress_node
          ↓
        planner_node
          ↓
        tool_node
          ↓
        correlate_and_validate_node
          ↘ (via refinement_router) planner_node or response_node
                                     ↓
                                 response_node
                                     ↓
                                    END
    """
    workflow = StateGraph(TopologyState)

    # Register nodes
    workflow.add_node("ingress_node", ingress_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("correlate_and_validate_node", correlate_and_validate_node)
    workflow.add_node("response_node", response_node)

    # Static edges
    workflow.add_edge(START, "ingress_node")
    workflow.add_edge("ingress_node", "planner")
    workflow.add_edge("planner", "tool_node")
    workflow.add_edge("tool_node", "correlate_and_validate_node")

    # Conditional edge: either refine (back to planner) or move to response
    workflow.add_conditional_edges(
        "correlate_and_validate_node",
        refinement_router,
        {
            "planner": "planner",
            "response_node": "response_node",
        },
    )

    # Final edge
    workflow.add_edge("response_node", END)

    return workflow.compile()
