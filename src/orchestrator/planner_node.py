from __future__ import annotations

from typing import Any, Dict

from .state_types import TopologyState


async def planner_node(state: TopologyState) -> TopologyState:
    """
    Planner node.

    In the full implementation this will:
      - Call an LLM (via llm.llm_factory) with a planner prompt
      - Produce a structured plan (which tools to call, with what arguments, and in what order)
      - Possibly include strategy flags (requires_strict_completeness, allow_partial, etc.)

    For now, we stub a simple static plan that says:
      - Call topology, inventory, comments, memory, hierarchy tools once.
    """
    user_input = state.get("user_input", "")

    # Simple placeholder plan structure
    plan: Dict[str, Any] = {
        "strategy": "simple",
        "description": "Call all tools once and correlate results.",
        "steps": [
            {"id": "step_topology", "tool": "topology_tool"},
            {"id": "step_inventory", "tool": "inventory_tool"},
            {"id": "step_comments", "tool": "comment_tool"},
            {"id": "step_memory", "tool": "memory_tool"},
            {"id": "step_hierarchy", "tool": "hierarchy_tool"},
        ],
        "metadata": {
            "from_user_input": user_input,
        },
    }

    state["plan"] = plan
    return state
