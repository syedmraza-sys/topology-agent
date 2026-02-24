from __future__ import annotations

from typing import Any, Dict

from .state_types import TopologyState


async def run_memory_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Query long-term chat memory (also pgvector or a dedicated table).

    In the real implementation, wire this to src/db/vector_client.py or a
    dedicated memory service.

    For now, return a minimal placeholder structure.
    """
    # Extract params from the scheduled plan step
    plan = state.get("plan", {})
    steps = plan.get("steps", [])
    
    params = {}
    for step in steps:
        if step.get("tool") in ["memory_tool", "memory_search_tool"]:
            params = step.get("params", {})
            break

    query_text = params.get("query_text", "")
    top_k = params.get("top_k", 3)

    session_id = state.get("session_id")
    memory_data: Dict[str, Any] = {
        "snippets": [],
        "metadata": {
            "source": "memory_tool_stub",
            "session_id": session_id,
            "query_text": query_text,
            "top_k": top_k,
        },
    }
    return memory_data
