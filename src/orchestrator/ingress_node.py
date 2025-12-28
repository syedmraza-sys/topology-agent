from __future__ import annotations

import time
from typing import Any, Dict, List

import structlog

from .state_types import TopologyState
from .metrics import NODE_INVOCATIONS, NODE_LATENCY

logger = structlog.get_logger("orchestrator.ingress")


async def ingress_node(state: TopologyState) -> TopologyState:
    """
    Build the initial state for the topology workflow.

    This node:
      - Normalizes user_input & ui_context
      - Initializes history / semantic_memory containers if missing
      - Sets retry_count / max_retries defaults
    """
    node_name = "ingress"
    log = logger.bind(node=node_name)
    if "request_id" in state:
        log = log.bind(request_id=state["request_id"])

    start = time.perf_counter()

    try:
        log.info(
            "node_start",
            user_input=state.get("user_input", ""),
        )

        # Normalize basic inputs
        user_input: str = state.get("user_input", "") or ""
        ui_context: Dict[str, Any] = state.get("ui_context", {}) or {}

        history: List[Dict[str, Any]] = state.get("history", []) or []
        semantic_memory: List[Dict[str, Any]] = state.get("semantic_memory", []) or []

        retry_count: int = state.get("retry_count", 0) or 0
        max_retries: int = state.get("max_retries", 1) or 1

        state["user_input"] = user_input
        state["ui_context"] = ui_context
        state["history"] = history
        state["semantic_memory"] = semantic_memory
        state["retry_count"] = retry_count
        state["max_retries"] = max_retries

        NODE_INVOCATIONS.labels(node=node_name, status="ok").inc()
        return state

    except Exception as exc:  # pragma: no cover
        NODE_INVOCATIONS.labels(node=node_name, status="error").inc()
        log.exception("node_error", error=str(exc))
        raise

    finally:
        duration = time.perf_counter() - start
        NODE_LATENCY.labels(node=node_name).observe(duration)
        log.info(
            "node_end",
            duration_ms=int(duration * 1000),
        )
