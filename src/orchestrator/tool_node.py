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
    start = time.perf_counter()

    try:
        log.info("node_start")

        # Topology graph
        state["topology_data"] = await _run_tool_with_metrics(
            "topology_tool",
            run_topology_tool,
            state,
        )

        # Inventory DB
        state["inventory_data"] = await _run_tool_with_metrics(
            "inventory_tool",
            run_inventory_tool,
            state,
        )

        # Comment RAG / pgvector
        state["comment_data"] = await _run_tool_with_metrics(
            "comment_tool",
            run_comment_tool,
            state,
        )

        # Long-term memory RAG (if implemented)
        state["memory_data"] = await _run_tool_with_metrics(
            "memory_tool",
            run_memory_tool,
            state,
        )

        # Low-latency hierarchy API
        state["hierarchy_data"] = await _run_tool_with_metrics(
            "hierarchy_tool",
            run_hierarchy_tool,
            state,
        )

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
