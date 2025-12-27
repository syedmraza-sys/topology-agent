from __future__ import annotations

import time
from typing import Any, Dict

import structlog

from .state_types import TopologyState
from .metrics import NODE_INVOCATIONS, NODE_LATENCY

logger = structlog.get_logger("orchestrator.response")


async def response_node(state: TopologyState) -> TopologyState:
    """
    Final node that ensures ui_response is present.

    Later you can plug in a response-polish LLM (get_response_chain) here;
    for now we just pass through ui_response from the correlate node.
    """
    node_name = "response"
    log = logger.bind(node=node_name)
    start = time.perf_counter()

    try:
        log.info("node_start")

        ui_response: Dict[str, Any] = state.get("ui_response", {}) or {}

        # In the future, you might call get_response_chain(...) here to
        # refine `natural_language_summary`.
        if "natural_language_summary" not in ui_response:
            ui_response["natural_language_summary"] = (
                "No response summary was generated."
            )

        state["ui_response"] = ui_response

        NODE_INVOCATIONS.labels(node=node_name, status="ok").inc()
        log.info(
            "node_completed",
            has_summary=bool(ui_response.get("natural_language_summary")),
        )

        return state

    except Exception as exc:  # pragma: no cover
        NODE_INVOCATIONS.labels(node=node_name, status="error").inc()
        log.exception("node_error", error=str(exc))
        raise

    finally:
        duration = time.perf_counter() - start
        NODE_LATENCY.labels(node=node_name).observe(duration)
        log.info("node_end", duration_ms=int(duration * 1000))
