from __future__ import annotations

from .state_types import TopologyState


async def response_node(state: TopologyState) -> TopologyState:
    """
    Final response node.

    In a future version this can:
      - Call an LLM to polish or explain the results in natural language.
      - Redact or shape data differently for different user roles.

    For now, it simply passes through ui_response prepared by correlate_and_validate_node.
    """
    # Ensure ui_response exists
    if "ui_response" not in state:
        state["ui_response"] = {
            "view_type": "path_view",
            "summary": {
                "total_circuits": 0,
                "impacted_circuits": 0,
                "impacted_customers": 0,
                "notes": "No data available.",
            },
            "paths": [],
            "circuits": [],
            "warnings": ["ui_response was missing; response_node filled defaults."],
            "partial": True,
            "natural_language_summary": "No topology results were produced.",
            "debug_state": {},
        }
        state["partial"] = True

    return state
