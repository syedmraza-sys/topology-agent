from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from .state_types import TopologyState
from ..dependencies import get_session_maker
from ..db import inventory_client


async def run_inventory_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Call the inventory DB (Postgres) and return inventory data.

    Current behavior:
      - If we have at least two selected_sites in ui_context, fetch circuits
        between those sites (optionally filtered by layer).
      - Otherwise, return an empty circuits list with metadata.

    Assumes a Postgres schema with tables like `inventory_circuits`.
    See src/db/inventory_client.py for expected columns.
    """
    # Extract params from the scheduled plan step
    plan = state.get("plan", {})
    steps = plan.get("steps", [])
    
    params = {}
    for step in steps:
        if step.get("tool") == "inventory_tool":
            params = step.get("params", {})
            break

    ui_context: Dict[str, Any] = state.get("ui_context", {}) or {}
    
    site_names: List[str] = params.get("site_names", [])
    device_ids = params.get("device_ids", [])
    circuit_ids = params.get("circuit_ids", [])
    query_type = params.get("query_type", "circuits")
    layer = params.get("layer") or ui_context.get("layer")

    # Gentle resolution of prior step variables. Topology tool outputs paths with hops.
    if isinstance(device_ids, str) and device_ids.startswith("$ref"):
        topology_data = state.get("topology_data") or {}
        resolved_devices = set()
        for path in topology_data.get("paths", []):
            resolved_devices.update(path.get("hops", []))
        device_ids = list(resolved_devices)

    if isinstance(circuit_ids, str) and circuit_ids.startswith("$ref"):
        # Topology tool doesn't naturally output circuit_ids yet, so default to empty
        circuit_ids = []

    if not site_names:
        site_names = ui_context.get("selected_sites", [])

    # If we don't know what sites to query, just return empty metadata.
    if len(site_names) < 2 and not device_ids and not circuit_ids:
        return {
            "circuits": [],
            "sites": [],
            "metadata": {
                "source": "inventory_tool",
                "reason": "insufficient site_names in ui_context or plan",
            },
        }

    # If we have exactly 2 sites, fetch circuits between them.
    # Otherwise, fallback to empty circuits for now unless device_ids trigger a separate query path.
    src_site = site_names[0] if len(site_names) >= 1 else None
    dst_site = site_names[1] if len(site_names) >= 2 else None

    SessionLocal = get_session_maker()

    circuits: List[Dict[str, Any]] = []
    sites: List[Dict[str, Any]] = []

    async with SessionLocal() as session:  # type: AsyncSession
        # Fetch circuits between the two sites
        if src_site and dst_site:
            # Fetch circuits between the two sites
            circuits = await inventory_client.get_circuits_by_sites(
                session,
                src_site=src_site,
                dst_site=dst_site,
                layer=layer,
                limit=500,
            )

       # print("DEBUG: Circuits:", circuits)

        # Fetch site records
        site_ids = set([s for s in site_names if s])
        if site_ids:
            sites = await inventory_client.get_sites_by_ids(
                session,
                site_ids=list(site_ids),
            )

    return {
        "circuits": circuits,
        "sites": sites,
        "metadata": {
            "source": "inventory_db",
            "src_site": src_site,
            "dst_site": dst_site,
            "layer": layer,
            "num_circuits": len(circuits),
        },
    }
