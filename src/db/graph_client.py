from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    # Neo4j async driver (optional; add neo4j to your dependencies if you use this)
    from neo4j import AsyncGraphDatabase  # type: ignore
except Exception:  # pragma: no cover
    AsyncGraphDatabase = None  # type: ignore


class GraphClient:
    """
    Thin wrapper around a graph database (e.g., Neo4j or Neptune).

    This version is designed for an async Neo4j driver, but you can adapt
    it for other graph stores. The orchestrator's topology_tool should
    depend on this client instead of the raw driver.
    """

    def __init__(self, driver: Any):
        self._driver = driver

    @classmethod
    async def from_neo4j(
        cls,
        uri: str,
        user: str,
        password: str,
        *,
        encrypted: bool = False,
    ) -> "GraphClient":
        """
        Create a GraphClient instance backed by a Neo4j async driver.

        Example URI: neo4j://host:7687
        """
        if AsyncGraphDatabase is None:
            raise RuntimeError(
                "neo4j package is not installed. Install `neo4j` to use GraphClient.from_neo4j()."
            )

        driver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password),
            encrypted=encrypted,
        )
        return cls(driver=driver)

    async def close(self) -> None:
        """
        Close the underlying driver/connection pool.
        """
        if self._driver is not None:
            await self._driver.close()

    async def run_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run a Cypher query and return the result as a list of dicts.

        This is a generic primitive that the topology_tool can build on
        (e.g., get paths between two sites, fetch neighbors, etc.).
        """
        if self._driver is None:
            raise RuntimeError("GraphClient driver is not initialized.")

        async with self._driver.session() as session:  # type: ignore[union-attr]
            result = await session.run(query, parameters or {})
            records = await result.data()
            # `data()` from neo4j returns a list of dict-like records already
            return [dict(r) for r in records]
