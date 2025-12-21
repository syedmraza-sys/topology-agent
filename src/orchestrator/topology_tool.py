from __future__ import annotations

from typing import Any, Dict

from .state_types import TopologyState


async def run_topology_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Call the underlying graph DB / topology service and return topology data.

    In the real implementation, wire this to src/db/graph_client.py and use:
      - src_site / dst_site or other entities extracted from state
      - ui_context filters (layer, region, etc.)

    For now, return a minimal placeholder structure.
    """
    user_input = state.get("user_input", "")

    topology_data: Dict[str, Any] = {
        "paths": [],
        "metadata": {
            "source": "topology_tool_stub",
            "query_summary": f"Stub topology result for: {user_input}",
        },
    }

    return topology_data
