from __future__ import annotations

from typing import Any, Dict, List, Optional

from .state_types import TopologyState
from ..dependencies import get_graph_client


async def run_topology_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Call the underlying graph DB / topology service and return topology data.

    Current behavior:
      - If a GraphClient is configured AND we have at least two selected_sites
        in ui_context, run a shortestPath query between them.
      - Otherwise, return a stubbed metadata-only payload.

    Assumes a Neo4j schema with nodes labeled :Site and relationships :LINK, e.g.:

        (s:Site {id: $src_site})-[:LINK*..10]->(d:Site {id: $dst_site})

    Adapt the Cypher query to your real graph schema later.
    """
    
    print("LOG: Inside topology_tool")
    user_input = state.get("user_input", "")
    ui_context: Dict[str, Any] = state.get("ui_context", {}) or {}

    selected_sites: List[str] = ui_context.get("selected_sites") or []
    layer: str = ui_context.get("layer") or "L2"

    print("LOG: Selected sites:", selected_sites)
    print("LOG: Layer:", layer) 
    print("LOG: User input:", user_input)
    graph_client = get_graph_client()

    # If no graph DB or not enough info, return stub.
    if graph_client is None or len(selected_sites) < 2:
        print("LOG: Returning stub")
        return {
            "paths": [],
            "metadata": {
                "source": "topology_tool_stub",
                "reason": "graph_client not configured or insufficient selected_sites",
                "query_summary": f"Stub topology result for: {user_input}",
            },
        }

    src_site = selected_sites[0]
    dst_site = selected_sites[1]

    # Simple shortestPath Cypher example; adapt to your real schema.
    # Changed query from id to name
    cypher = """
    MATCH (s:Site {name: $src_site}), (d:Site {name: $dst_site}) 
    MATCH p = shortestPath((s)-[:LINK*..10]->(d))
    RETURN [n IN nodes(p) | n.id] AS hops
    """

    print("LOG:Running cypher query:", cypher)
    print("LOG: With params:", {
        "src_site": src_site,
        "dst_site": dst_site,
    })  

    try:
        records = await graph_client.run_cypher(
            cypher,
            {
                "src_site": src_site,
                "dst_site": dst_site,
            },
        )
    except Exception as exc:
        # On error, fall back to stub but indicate degradation.
        print("LOG: Graph client error:", exc)
        return {
            "paths": [],
            "metadata": {
                "source": "topology_tool_graph_error",
                "error": str(exc),
                "query_summary": f"Failed to fetch path for {src_site} -> {dst_site}",
            },
        }

    paths: List[Dict[str, Any]] = []
    for rec in records:
        hops = rec.get("hops") or []
        if not isinstance(hops, list):
            continue
        paths.append(
            {
                "src_site": src_site,
                "dst_site": dst_site,
                "layer": layer,
                "hops": hops,
            }
        )

    print("LOG: Paths:", paths)

    return {
        "paths": paths,
        "metadata": {
            "source": "topology_graph_db",
            "src_site": src_site,
            "dst_site": dst_site,
            "layer": layer,
            "num_paths": len(paths),
        },
    }
