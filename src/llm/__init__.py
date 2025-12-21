from __future__ import annotations

"""
LLM utilities for the topology agent.

This package provides:
- Backend-agnostic LLM factories (OpenAI / Bedrock / Vertex / vLLM)
- Prompt templates for planner, validator, and response refinement
- Optional LangSmith tracing configuration
"""

from .llm_factory import (
    get_planner_model,
    get_validator_model,
    get_response_model,
    get_planner_chain,
    get_validator_chain,
    get_response_chain,
)
from .tracing_langsmith import configure_langsmith_tracing

__all__ = [
    "get_planner_model",
    "get_validator_model",
    "get_response_model",
    "get_planner_chain",
    "get_validator_chain",
    "get_response_chain",
    "configure_langsmith_tracing",
]
