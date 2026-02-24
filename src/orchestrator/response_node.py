from __future__ import annotations

import time
from typing import Any, Dict

import json
import structlog

from .state_types import TopologyState
from .metrics import NODE_INVOCATIONS, NODE_LATENCY
from ..llm.llm_factory import get_response_chain
from ..config import get_settings

logger = structlog.get_logger("orchestrator.response")


async def response_node(state: TopologyState) -> TopologyState:
    """
    Final node that ensures ui_response is present and refined.

    Calls get_response_chain to produce a clear, concise natural language
    explanation based on the merged data.
    """
    node_name = "response"
    log = logger.bind(node=node_name)
    if "request_id" in state:
        log = log.bind(request_id=state["request_id"])
        
    start = time.perf_counter()

    try:
        log.info("node_start")

        ui_response: Dict[str, Any] = state.get("ui_response", {}) or {}
        question = state.get("user_input", "")
        
        # Prepare inputs for the response chain
        # We pass a subset of the UI response as 'structured_data' to avoid prompt bloat
        structured_subset = {
            "summary": ui_response.get("summary"),
            "paths": ui_response.get("paths", [])[:3], # Top 3 paths
            "circuits": ui_response.get("circuits", [])[:10], # First 10 circuits
            "warnings": ui_response.get("warnings", []),
            "partial": ui_response.get("partial", False)
        }

        settings = get_settings()
        response_chain = get_response_chain(settings)
        
        log.info("response_llm_invoke_start")
        
        try:
            result = await response_chain.ainvoke({
                "question": question,
                "structured_data": json.dumps(structured_subset, indent=2),
                "draft_summary": ui_response.get("natural_language_summary", "")
            })
            
            refined_summary = result.content if hasattr(result, "content") else str(result)
            ui_response["natural_language_summary"] = refined_summary.strip()
            
            log.info("response_llm_invoke_success")
        except Exception as exc:
            log.error("response_llm_invoke_failed", error=str(exc))
            # Fallback is already in ui_response["natural_language_summary"] 
            # from the correlate node.

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
