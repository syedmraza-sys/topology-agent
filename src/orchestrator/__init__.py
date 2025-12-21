from __future__ import annotations

"""
Orchestrator package for the topology agent.

This package wires together:
- State types
- LangGraph workflow
- Nodes (ingress, planner, tools, correlation/validation, response)
- Tool wrappers for graph DB, inventory DB, vector DB, etc.
"""

from .workflow import build_workflow  # re-export for convenience

__all__ = ["build_workflow"]
