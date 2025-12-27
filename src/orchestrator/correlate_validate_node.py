from __future__ import annotations

import time
from typing import Any, Dict, List

import structlog

from .state_types import TopologyState
from .metrics import NODE_INVOCATIONS, NODE_LATENCY

logger = structlog.get_logger("orchestrator.correlate")


async def correlate_and_validate_node(state: TopologyState) -> TopologyState:
    """
    Correlate tool results into a unified domain picture and validate completeness.

    at first, the logic is deliberately simple:
      - Build empty summary & UI structures.
      - Mark validation as "ok" and no refinement needed.

    For now, the logic is simple:
      - Use topology_data.paths and inventory_data.circuits as-is.
      - Attach comment RAG results to the UI response.
      - Set total_circuits/impacted_circuits based on circuits length.
      - Mark validation as ok (no refinement).

    Later you will:
      - Merge topology_data, inventory_data, hierarchy_data into paths/circuits/impact.
      - Run deterministic checks (missing circuits, inconsistent states).
      - Optionally call an LLM-as-judge for explanation quality.
    """

    node_name = "correlate_validate"
    log = logger.bind(node=node_name)
    start = time.perf_counter()

    try:
        log.info("node_start")

        topology_data: Dict[str, Any] = state.get("topology_data", {}) or {}
        inventory_data: Dict[str, Any] = state.get("inventory_data", {}) or {}
        comment_data: Dict[str, Any] = state.get("comment_data", {}) or {}
        hierarchy_data: Dict[str, Any] = state.get("hierarchy_data", {}) or {}

        # Very simple stub correlation:
        paths: List[Dict[str, Any]] = topology_data.get("paths", [])  # should match TopologyPath schema
        circuits: List[Dict[str, Any]] = inventory_data.get("circuits", [])
        comments: List[Dict[str, Any]] = comment_data.get("comments", []) or []

        total_circuits = len(circuits)
        # For now, assume all fetched circuits are "impacted"; later you can
        # compute this based on outage state, path membership, etc.
        impacted_circuits = total_circuits

        summary = {
            "total_circuits": total_circuits,
            "impacted_circuits": impacted_circuits,
            "impacted_customers": 0,  # TODO: compute from hierarchy/inventory
            "notes": "Summary derived from topology, inventory, and comment RAG; impact logic is placeholder.",
        }

        warnings: List[str] = []
        partial = False

        # Basic validation stub
        validation: Dict[str, Any] = {
            "status": "ok",
            "needs_refinement": False,
            "warnings": warnings.copy(),
        }

        state["validation"] = validation

        # Prepare a draft ui_response structure; response_node can refine it further.
        ui_response: Dict[str, Any] = {
            "view_type": "path_view",
            "summary": summary,
            "paths": paths,
            "circuits": circuits,
            "comments": comments,  # <- expose comment RAG results to UI
            "warnings": warnings,
            "partial": partial,
            "natural_language_summary": "This is a placeholder summary for the topology query.",
            "debug_state": {},
        }

        state["ui_response"] = ui_response
        state["partial"] = partial

        NODE_INVOCATIONS.labels(node=node_name, status="ok").inc()
        log.info(
            "node_completed",
            total_circuits=total_circuits,
            num_paths=len(paths),
            num_comments=len(comments),
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