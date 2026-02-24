from __future__ import annotations

from typing import Any, Dict

from .state_types import TopologyState


async def run_hierarchy_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Call low-latency hierarchy APIs (circuit hierarchy, service hierarchy, etc).

    In the real implementation, wire this to src/db/hierarchy_client.py or
    an external REST/GraphQL client.

    For now, return a minimal placeholder structure.
    """
    # Extract params from the scheduled plan step
    plan = state.get("plan", {})
    steps = plan.get("steps", [])
    
    params = {}
    for step in steps:
        if step.get("tool") == "hierarchy_tool":
            params = step.get("params", {})
            break

    query_type = params.get("query_type", "site_info")
    site_names = params.get("site_names", [])
    include_metadata = params.get("include_metadata", False)

    if not site_names:
        ui_context: Dict[str, Any] = state.get("ui_context", {}) or {}
        site_names = ui_context.get("selected_sites", [])

    hierarchy_data: Dict[str, Any] = {
        "hierarchies": [],
        "metadata": {
            "source": "hierarchy_tool_stub",
            "query_type": query_type,
            "sites_checked": len(site_names),
        },
    }
    return hierarchy_data
