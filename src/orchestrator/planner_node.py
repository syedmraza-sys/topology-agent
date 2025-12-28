from __future__ import annotations

import json
import time
from typing import Any, Dict

import structlog

from .state_types import TopologyState
from .metrics import NODE_INVOCATIONS, NODE_LATENCY
from ..config import get_settings
from ..llm.llm_factory import get_planner_chain
from .domain_metrics import PLANNER_FALLBACK_USED

logger = structlog.get_logger("orchestrator.planner")


def _fallback_plan(state: TopologyState) -> Dict[str, Any]:
    """
    Fallback plan used when the LLM output is invalid or planning fails.

    This preserves your original behavior: call all tools once.
    """
    PLANNER_FALLBACK_USED.inc()
    
    user_input = state.get("user_input", "")

    return {
        "strategy": "fallback_simple",
        "description": "Fallback: call all tools once and correlate results.",
        "steps": [
            {"id": "step_topology", "tool": "topology_tool", "params": {}},
            {"id": "step_inventory", "tool": "inventory_tool", "params": {}},
            {"id": "step_comments", "tool": "comment_tool", "params": {}},
            {"id": "step_memory", "tool": "memory_tool", "params": {}},
            {"id": "step_hierarchy", "tool": "hierarchy_tool", "params": {}},
        ],
        "metadata": {
            "from_user_input": user_input,
            "fallback_reason": "llm_planner_failed_or_invalid_json",
        },
    }

def _parse_plan_from_llm_output(raw_text: str, state: TopologyState) -> Dict[str, Any]:
    """
    Parse the LLM output as JSON and validate basic structure.

    If parsing or validation fails, return the fallback plan.
    """
    # Clean up potential markdown formatting (e.g. ```json ... ```)
    cleaned_text = raw_text.strip()
    if cleaned_text.startswith("```"):
        # Remove opening ```json or ```
        cleaned_text = cleaned_text.split("\n", 1)[-1]
        # Remove closing ```
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text.rsplit("\n", 1)[0]
    
    try:
        data = json.loads(cleaned_text)
    except Exception as exc:
        logger.warning(
            "planner_llm_json_parse_failed",
            error=str(exc),
            raw_text_snippet=raw_text[:200],
        )
        state["planning_error"] = f"JSON parse error: {exc}"
        return _fallback_plan(state)

    # Basic sanity checks
    if not isinstance(data, dict) or "steps" not in data:
        logger.warning(
            "planner_llm_invalid_structure",
            reason="missing_steps",
        )
        state["planning_error"] = "Planner LLM output missing 'steps'."
        return _fallback_plan(state)

    steps = data.get("steps", [])
    if not isinstance(steps, list) or not steps:
        logger.warning(
            "planner_llm_invalid_structure",
            reason="steps_not_list_or_empty",
        )
        state["planning_error"] = "Planner LLM 'steps' must be a non-empty list."
        return _fallback_plan(state)

    # Ensure each step has at least an id and tool
    for idx, step in enumerate(steps):
        if not isinstance(step, dict) or "tool" not in step:
            logger.warning(
                "planner_llm_invalid_step",
                index=idx,
                step=step,
            )
            state["planning_error"] = f"Invalid step at index {idx}."
            return _fallback_plan(state)
        step.setdefault("id", f"step_{idx}")
        step.setdefault("params", {})

    # If we get here, we consider the plan acceptable
    return data


async def planner_node(state: TopologyState) -> TopologyState:
    """
    LLM-based planner node.

    - Calls the planner chain (prompt + model).
    - Expects valid JSON in the response.
    - On success: stores structured plan in state["plan"].
    - On failure: stores a fallback plan and sets state["planning_error"].
    """
    
    node_name = "planner"
    log = logger.bind(node=node_name)
    request_id = state.get("request_id")
    if request_id:
        log = log.bind(request_id=request_id)

    start = time.perf_counter()
    
    settings = get_settings()
    question = state.get("user_input", "") or ""

    ui_context = state.get("ui_context", {}) or {}
    history = state.get("history", []) or []
    memory_snippets = state.get("semantic_memory", []) or []
    previous_plan = state.get("plan") or {}
    validation_feedback = state.get("validation") or {}

    try:
        log.info(
            "node_start",
            question=question,
            has_previous_plan=bool(previous_plan),
        )

        if not question.strip():
            # Degenerate case: no question; just use fallback plan.
            logger.info("planner_empty_question_using_fallback")
            state["plan"] = _fallback_plan(state)
            state["plan_raw"] = ""
            NODE_INVOCATIONS.labels(node=node_name, status="ok").inc()
            return state

        planner_chain = get_planner_chain(settings)

        # Build planner input (matches planner_prompt.py template)
        planner_input: Dict[str, Any] = {
            "question": question,
            "ui_context": ui_context,
            "history": history,
            "memory_snippets": memory_snippets,
            "previous_plan": previous_plan,
            "validation_feedback": validation_feedback,
        }

        logger.info("planner_llm_invoke_start")

        try:
            # planner_chain is (prompt | model). It will return a ChatMessage-like object.
            result = await planner_chain.ainvoke(planner_input)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.error("planner_llm_invoke_failed", error=str(exc), exc_info=True)
            state["plan"] = _fallback_plan(state)
            state["plan_raw"] = ""
            state["planning_error"] = f"Planner LLM invoke error: {exc}"
            return state

        # Extract raw text from the model output
        try:
            raw_text = result.content if hasattr(result, "content") else str(result)
        except Exception:
            raw_text = str(result)

        state["plan_raw"] = raw_text

        plan = _parse_plan_from_llm_output(raw_text, state)
        state["plan"] = plan

        print("DEBUG: state plan ", state["plan"])  
        print("DEBUG: state plan_raw ", state["plan_raw"])  
        print("DEBUG: state planning_error ", state["planning_error"])  
    
        NODE_INVOCATIONS.labels(node=node_name, status="ok").inc()        
        
        logger.info(
            "planner_llm_invoke_success",
            strategy=plan.get("strategy", "unknown"),
            num_steps=len(plan.get("steps", [])),
            has_error=bool(state.get("planning_error")),
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
