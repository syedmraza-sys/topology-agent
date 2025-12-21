from __future__ import annotations

from typing import Any, Dict

from .state_types import TopologyState


async def ingress_node(state: TopologyState) -> TopologyState:
    """
    Normalize and enrich the initial state coming from the API layer.

    - Ensure ui_context, history, semantic_memory are present.
    - Set default retry counters if missing.
    - In a future version, you can:
      * run entity extraction
      * pre-populate semantic_memory from vector DB
    """
    new_state: Dict[str, Any] = dict(state)  # shallow copy

    new_state.setdefault("ui_context", {})
    new_state.setdefault("history", [])
    new_state.setdefault("semantic_memory", [])

    # Retry / refinement defaults
    new_state.setdefault("retry_count", 0)
    new_state.setdefault("max_retries", 1)

    return new_state  # type: ignore[return-value]
