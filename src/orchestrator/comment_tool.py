from __future__ import annotations

from typing import Any, Dict

from .state_types import TopologyState


async def run_comment_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Query pgvector for user comments / tickets relevant to this query.

    In the real implementation, wire this to src/db/vector_client.py.

    For now, return a minimal placeholder structure.
    """
    user_input = state.get("user_input", "")
    comment_data: Dict[str, Any] = {
        "comments": [],
        "metadata": {
            "source": "comment_tool_stub",
            "query_summary": f"No comments fetched for: {user_input}",
        },
    }
    return comment_data
