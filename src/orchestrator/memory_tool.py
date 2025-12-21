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
    session_id = state.get("session_id")
    memory_data: Dict[str, Any] = {
        "snippets": [],
        "metadata": {
            "source": "memory_tool_stub",
            "session_id": session_id,
        },
    }
    return memory_data
