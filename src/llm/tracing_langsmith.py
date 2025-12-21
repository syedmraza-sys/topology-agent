from __future__ import annotations

import os

from ..config import Settings


def configure_langsmith_tracing(settings: Settings) -> None:
    """
    Configure environment variables so that LangChain/LangGraph
    send traces to LangSmith, if configured.

    This does NOT import langsmith or langchain directly; it just sets
    env vars that those libraries respect.

    Expected in Settings:
      - langsmith_api_key
      - langsmith_project
      - langsmith_endpoint (optional)
    """
    api_key = settings.langsmith_api_key
    project = settings.langsmith_project
    endpoint = settings.langsmith_endpoint

    if not api_key or not project:
        # Tracing is disabled if either is missing
        return

    # Newer LangSmith integration prefers LANGSMITH_* variables
    os.environ.setdefault("LANGSMITH_API_KEY", api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", project)

    if endpoint:
        os.environ.setdefault("LANGSMITH_ENDPOINT", str(endpoint))

    # Enable LangChain v2 tracing if desired
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

    # Backward-compat global defaults (optional)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", os.environ.get("LANGSMITH_ENDPOINT", ""))
    os.environ.setdefault("LANGCHAIN_API_KEY", api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", project)
