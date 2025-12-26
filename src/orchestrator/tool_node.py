from __future__ import annotations

from .state_types import TopologyState
from .comment_tool import run_comment_tool
from .hierarchy_tool import run_hierarchy_tool
from .inventory_tool import run_inventory_tool
from .memory_tool import run_memory_tool
from .topology_tool import run_topology_tool


async def tool_node(state: TopologyState) -> TopologyState:
    """
    Execute the tools needed for this query.

    For now, we simply:
      - call topology, inventory, comments, memory, hierarchy tools sequentially
      - store their results into state["*_data"]

    Later, you can:
      - read state["plan"]["steps"] and selectively call tools
      - add parallelism or more complex scheduling.
    """
    
    # print("LOG: Running tool_node")

    # Topology
    state["topology_data"] = await run_topology_tool(state)

    # Inventory
    state["inventory_data"] = await run_inventory_tool(state)

    # Comments
    state["comment_data"] = await run_comment_tool(state)

    # Memory
    state["memory_data"] = await run_memory_tool(state)

    # Hierarchy
    state["hierarchy_data"] = await run_hierarchy_tool(state)

    # print("DEBUG: state comment_data ", state["comment_data"])
    
    return state
