from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class HierarchyClient:
    """
    Thin async client for low-latency hierarchy APIs.

    This is intentionally generic: you can point it at an internal microservice
    that exposes endpoints like:

      GET /hierarchy/circuit/{circuit_id}
      GET /hierarchy/service/{service_id}

    and adapt the methods below as needed.
    """

    def __init__(self, base_url: str, *, timeout: float = 5.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def get_circuit_hierarchy(
        self,
        circuit_id: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Dict[str, Any]:
        """
        Fetch hierarchy information for a given circuit.

        Returns a dict that can be passed through to the orchestrator's
        hierarchy_tool, which will shape it into the domain model needed.
        """
        url = f"{self._base_url}/hierarchy/circuit/{circuit_id}"

        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
            close_client = True

        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "circuit_id": circuit_id,
                "hierarchy": data,
                "source": "hierarchy_api",
            }
        finally:
            if close_client:
                await client.aclose()

    async def get_bulk_circuit_hierarchy(
        self,
        circuit_ids: List[str],
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch hierarchy information for multiple circuits.

        This is just a simple loop for now; you can switch to a proper
        bulk API or concurrent calls later.
        """
        results: List[Dict[str, Any]] = []
        for cid in circuit_ids:
            h = await self.get_circuit_hierarchy(circuit_id=cid, client=client)
            results.append(h)
        return results
