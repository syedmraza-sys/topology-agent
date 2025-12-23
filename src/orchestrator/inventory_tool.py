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
    ui_context: Dict[str, Any] = state.get("ui_context", {}) or {}
    selected_sites: List[str] = ui_context.get("selected_sites") or []
    layer: str | None = ui_context.get("layer")

    # If we don't know what sites to query, just return empty metadata.
    if len(selected_sites) < 2:
        return {
            "circuits": [],
            "sites": [],
            "metadata": {
                "source": "inventory_tool",
                "reason": "insufficient selected_sites in ui_context",
            },
        }

    src_site = selected_sites[0]
    dst_site = selected_sites[1]

    SessionLocal = get_session_maker()

    circuits: List[Dict[str, Any]] = []
    sites: List[Dict[str, Any]] = []

    async with SessionLocal() as session:  # type: AsyncSession
        # Fetch circuits between the two sites
        circuits = await inventory_client.get_circuits_by_sites(
            session,
            src_site=src_site,
            dst_site=dst_site,
            layer=layer,
            limit=500,
        )

        print("LOG: Circuits:", circuits)

        # Optionally fetch full site records for the endpoints (and maybe others)
        site_ids = {src_site, dst_site}
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
