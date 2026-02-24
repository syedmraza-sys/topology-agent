from __future__ import annotations

import time
from typing import Any, Dict, Callable, Awaitable

import structlog

from .state_types import TopologyState
from .metrics import NODE_INVOCATIONS, NODE_LATENCY, TOOL_INVOCATIONS, TOOL_LATENCY
from .topology_tool import run_topology_tool
from .inventory_tool import run_inventory_tool
from .comment_tool import run_comment_tool
from .memory_tool import run_memory_tool
from .hierarchy_tool import run_hierarchy_tool
from .outage_tool import run_outage_tool

logger = structlog.get_logger("orchestrator.tools")


async def _run_tool_with_metrics(
    name: str,
    func: Callable[[TopologyState], Awaitable[Dict[str, Any]]],
    state: TopologyState,
) -> Dict[str, Any]:
    """
    Helper to wrap each tool invocation with logging + Prometheus metrics.
    """
    log = logger.bind(tool=name)
    if "request_id" in state:
        log = log.bind(request_id=state["request_id"])

    start = time.perf_counter()

    try:
        log.info("tool_start")
        result = await func(state)
        TOOL_INVOCATIONS.labels(tool=name, status="ok").inc()
        return result
    except Exception as exc:  # pragma: no cover
        TOOL_INVOCATIONS.labels(tool=name, status="error").inc()
        log.exception("tool_error", error=str(exc))
        raise
    finally:
        duration = time.perf_counter() - start
        TOOL_LATENCY.labels(tool=name).observe(duration)
        log.info("tool_end", duration_ms=int(duration * 1000))


async def tool_node(state: TopologyState) -> TopologyState:
    """
    Single node responsible for invoking all necessary tools.

    For now, we still call all tools once. Later you can map this to the
    planner's `plan["steps"]` to selectively invoke tools.

    This node logs and records Prometheus metrics for:
      - the node itself
      - each tool invocation
    """
    node_name = "tool_node"
    log = logger.bind(node=node_name)
    if "request_id" in state:
        log = log.bind(request_id=state["request_id"])

    start = time.perf_counter()

    try:
        log.info("node_start")

        plan = state.get("plan", {})
        steps = plan.get("steps", [])

        # If we have no plan or it's empty, default to calling them all
        # or just iterating over them (fallback_plan handles empty logic).
        tool_dispatch = {
            "topology_tool": (run_topology_tool, "topology_data"),
            "inventory_tool": (run_inventory_tool, "inventory_data"),
            "comment_tool": (run_comment_tool, "comment_data"),
            "comments_search_tool": (run_comment_tool, "comment_data"),
            "outage_tool": (run_outage_tool, "outage_data"),
            "memory_tool": (run_memory_tool, "memory_data"),
            "hierarchy_tool": (run_hierarchy_tool, "hierarchy_data"),
        }

        # Initialize state keys to None so downstream nodes don't KeyError
        for _, data_key in tool_dispatch.values():
            state[data_key] = None

        if not steps:
            logger.warning("tool_node_no_steps", plan=plan)
            # You can choose to fallback to calling them all here if preferred.
            
        for step in steps:
            tool_name = step.get("tool")
            if tool_name in tool_dispatch:
                func, data_key = tool_dispatch[tool_name]
                state[data_key] = await _run_tool_with_metrics(
                    tool_name,
                    func,
                    state,
                )
            else:
                logger.warning("tool_node_unknown_tool", tool_name=tool_name)

        NODE_INVOCATIONS.labels(node=node_name, status="ok").inc()
        return state

    except Exception as exc:  # pragma: no cover
        NODE_INVOCATIONS.labels(node=node_name, status="error").inc()
        log.exception("node_error", error=str(exc))
        raise

    finally:
        duration = time.perf_counter() - start
        NODE_LATENCY.labels(node=node_name).observe(duration)
        log.info("node_end", duration_ms=int(duration * 1000))
