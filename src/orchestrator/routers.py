from __future__ import annotations

from .state_types import TopologyState


def execution_router(state: TopologyState) -> str:
    """
    Decide which execution node to run next.

    In this first version we only have a single tool_node, so we always
    route to "tool_node". When you later split tools into multiple nodes
    (topology, inventory, comments, etc.), extend this function to pick
    the next node based on the plan in state["plan"].
    """
    # Placeholder for future expansion (multi-tool execution).
    return "tool_node"


def refinement_router(state: TopologyState) -> str:
    """
    Decide whether to refine (re-plan & re-execute) or move to response.

    correlate_validate_node can set:
      state["validation"]["needs_refinement"] = True/False

    We also respect state["max_retries"] to avoid infinite loops.
    """
    validation = state.get("validation") or {}
    needs_refinement = bool(validation.get("needs_refinement"))
    retry_count = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 0))

    if needs_refinement and retry_count < max_retries:
        # Increment retry counter and go back to planner
        state["retry_count"] = retry_count + 1
        return "planner"

    # Default: go to response_node
    return "response_node"
