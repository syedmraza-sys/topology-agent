from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class TopologyState(TypedDict, total=False):
    """
    Shared state that flows through the LangGraph topology workflow.

    The API layer seeds a subset of this; nodes progressively enrich it.
    """

    # === Core input ===
    user_input: str
    ui_context: Dict[str, Any]
    session_id: Optional[str]
    request_id: Optional[str]  # Correlation ID for logging/tracing

    # Conversation context (can be populated by a memory node later)
    history: List[Dict[str, Any]]
    semantic_memory: List[Dict[str, Any]]

    # Retry / refinement tracking
    retry_count: int
    max_retries: int

    # === Planner output ===
    # For now, this is a loose dict; you can tighten it later with Pydantic models.
    plan: Dict[str, Any]
    plan_raw: str                        # raw LLM text output (for debugging)
    planning_error: Optional[str]        # error message if parsing failed
    
    # === Tool results ===
    topology_data: Dict[str, Any]
    inventory_data: Dict[str, Any]
    comment_data: Dict[str, Any]
    memory_data: Dict[str, Any]
    hierarchy_data: Dict[str, Any]

    # === Validation / correlation ===
    validation: Dict[str, Any]

    # === Final UI payload ===
    ui_response: Dict[str, Any]
    partial: bool
