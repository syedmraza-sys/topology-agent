from __future__ import annotations

import time
from typing import Any, Dict, List

import structlog

from .state_types import TopologyState
from .metrics import NODE_INVOCATIONS, NODE_LATENCY
from .domain_metrics import COMMENT_RAG_HIT, COMMENT_RAG_MISS

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
    if "request_id" in state:
        log = log.bind(request_id=state["request_id"])
        
    start = time.perf_counter()

    try:
        log.info("node_start")

        topology_data: Dict[str, Any] = state.get("topology_data") or {}
        inventory_data: Dict[str, Any] = state.get("inventory_data") or {}
        comment_data: Dict[str, Any] = state.get("comment_data") or {}
        hierarchy_data: Dict[str, Any] = state.get("hierarchy_data") or {}
        outage_data: Dict[str, Any] = state.get("outage_data") or {}

        # 1. Map Alarms for efficient lookup
        # outage_tool returns { "active_alarms": [...] }
        alarms = outage_data.get("active_alarms", [])
        alarms_by_eid: Dict[str, List[Dict[str, Any]]] = {}
        for alarm in alarms:
            eid = alarm.get("element_id")
            if eid:
                alarms_by_eid.setdefault(eid, []).append(alarm)

        # 2. Enrich Circuits with Alarm Data
        circuits: List[Dict[str, Any]] = inventory_data.get("circuits", [])
        impacted_circuits_count = 0
        
        for circuit in circuits:
            cid = circuit.get("circuit_id")
            # Attach direct alarms for this circuit
            circuit_alarms = alarms_by_eid.get(cid, [])
            
            # (Heuristic) Also check if the sites it connects might have alarms
            # Logic depends on inventory schema; assuming src_site/dst_site keys
            src_site = circuit.get("src_site")
            dst_site = circuit.get("dst_site")
            if src_site in alarms_by_eid:
                circuit_alarms.extend(alarms_by_eid[src_site])
            if dst_site in alarms_by_eid:
                circuit_alarms.extend(alarms_by_eid[dst_site])

            circuit["alarms"] = circuit_alarms
            circuit["is_impacted"] = len(circuit_alarms) > 0
            if circuit["is_impacted"]:
                impacted_circuits_count += 1

        # 3. Enrich Topology Paths with Alarm Data
        paths: List[Dict[str, Any]] = topology_data.get("paths", [])
        for path in paths:
            path_alarms = []
            # 'hops' are IDs of sites or devices in the path
            for hop_id in path.get("hops", []):
                if hop_id in alarms_by_eid:
                    path_alarms.extend(alarms_by_eid[hop_id])
            
            path["alarms"] = path_alarms
            path["is_impacted"] = len(path_alarms) > 0

        # 4. Handle Comment RAG metrics
        comments: List[Dict[str, Any]] = comment_data.get("comments", [])
        if comment_data:
            if comments:
                COMMENT_RAG_HIT.inc()
            else:
                COMMENT_RAG_MISS.inc()

        # 5. Global Summary and Warnings
        warnings: List[str] = []
        partial = False

        # Detect if any tool was skipped by circuit breaker
        tool_results = [
            ("topology", topology_data),
            ("inventory", inventory_data),
            ("outage", outage_data),
            ("comments", comment_data)
        ]
        for t_name, t_data in tool_results:
            if t_data.get("error") == "circuit_breaker_open":
                warnings.append(f"Tool '{t_name}' was skipped due to recurring failures (circuit breaker open).")
                partial = True

        total_circuits = len(circuits)
        
        summary = {
            "total_circuits": total_circuits,
            "impacted_circuits": impacted_circuits_count,
            "impacted_customers": 0, # TODO: integrate hierarchy_data when schema is ready
            "notes": "Correlation complete. Alarms merged into circuits and topology paths.",
        }

        # 6. Validation Logic (Determine if Refinement is needed)
        # If user asked a question but we have ZERO data and no errors, maybe we need to refine.
        needs_refinement = False
        if not paths and not circuits and not partial:
             # Basic heuristic: if we found nothing, maybe the planner needs a broader search?
             # But for now, let's keep it False to avoid loops.
             pass

        validation: Dict[str, Any] = {
            "status": "partial" if partial else "ok",
            "needs_refinement": needs_refinement,
            "warnings": warnings,
        }

        state["validation"] = validation
        state["partial"] = partial

        # 7. Final UI Response Preparation
        ui_response: Dict[str, Any] = {
            "view_type": "path_view" if paths else "circuit_view",
            "summary": summary,
            "paths": paths,
            "circuits": circuits,
            "comments": comments,
            "warnings": warnings,
            "partial": partial,
            "natural_language_summary": f"Found {total_circuits} circuits, {impacted_circuits_count} of which are impacted by active outages.",
            "debug_state": {
                "num_alarms": len(alarms),
                "num_hops_checked": sum(len(p.get("hops", [])) for p in paths)
            },
        }

        state["ui_response"] = ui_response

        NODE_INVOCATIONS.labels(node=node_name, status="ok").inc()
        log.info(
            "node_completed",
            total_circuits=total_circuits,
            affected=impacted_circuits_count,
            partial=partial
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