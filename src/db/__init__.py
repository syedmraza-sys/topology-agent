from __future__ import annotations

"""
Database client layer for the topology agent.

This package provides thin async clients/wrappers for:
- Inventory DB (Postgres)
- Hierarchy APIs
- Vector search (pgvector in Postgres)
- Graph DB (Neo4j / Neptune)

The orchestrator tools (in src/orchestrator/*_tool.py) should depend on these
modules rather than talking to raw drivers directly.
"""

__all__ = [
    "inventory_client",
    "hierarchy_client",
    "vector_client",
    "graph_client",
]
