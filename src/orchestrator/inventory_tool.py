from __future__ import annotations

from typing import Any, Dict

from .state_types import TopologyState


async def run_inventory_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Call the inventory DB (Postgres) and return inventory data.

    In the real implementation, wire this to src/db/inventory_client.py.

    For now, return a minimal placeholder structure.
    """
    inventory_data: Dict[str, Any] = {
        "circuits": [],
        "sites": [],
        "metadata": {
            "source": "inventory_tool_stub",
        },
    }
    return inventory_data
