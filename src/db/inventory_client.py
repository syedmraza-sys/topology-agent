from __future__ import annotations

from typing import Any, Dict, List, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_circuits_by_sites(
    session: AsyncSession,
    src_site: str,
    dst_site: str,
    *,
    layer: str | None = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Fetch circuits between two sites from the inventory database.

    This assumes the existence of an `inventory_circuits` table with at least:
      - id (text)
      - src_site (text)
      - dst_site (text)
      - layer (text)
      - status (text)
      - metadata (jsonb)

    Adjust the table/column names as needed in your migrations.
    """
    query = text(
        """
        SELECT
            id,
            src_site,
            dst_site,
            layer,
            status,
            metadata
        FROM inventory_circuits
        WHERE src_site in (SELECT id FROM inventory_sites WHERE name = :src_site)
          AND dst_site in (SELECT id FROM inventory_sites WHERE name = :dst_site)
          {layer_clause}
        LIMIT :limit
        """
        .format(layer_clause="AND layer = :layer" if layer else "")
    )

    print("LOG: Running SQL query:", query)
    print("LOG: With params:", {
        "src_site": src_site,
        "dst_site": dst_site,
        "layer": layer,
        "limit": limit,
    })
    
    params: Dict[str, Any] = {
        "src_site": src_site,
        "dst_site": dst_site,
        "limit": limit,
    }
    if layer:
        params["layer"] = layer

    result = await session.execute(query, params)
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def get_circuits_by_ids(
    session: AsyncSession,
    circuit_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    """
    Fetch circuits by ID from the inventory database.
    """
    if not circuit_ids:
        return []

    query = text(
        """
        SELECT
            id,
            src_site,
            dst_site,
            layer,
            status,
            metadata
        FROM inventory_circuits
        WHERE id = ANY(:circuit_ids)
        """
    )
    result = await session.execute(query, {"circuit_ids": list(circuit_ids)})
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def get_sites_by_ids(
    session: AsyncSession,
    site_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    """
    Fetch site records by ID.

    Assumes an `inventory_sites` table with (at least):
      - id (text)
      - name (text)
      - region (text)
      - metadata (jsonb)
    """
    if not site_ids:
        return []

    query = text(
        """
        SELECT
            id,
            name,
            region,
            metadata
        FROM inventory_sites
        WHERE id = ANY(:site_ids)
        """
    )
    result = await session.execute(query, {"site_ids": list(site_ids)})
    rows = result.mappings().all()
    return [dict(row) for row in rows]
