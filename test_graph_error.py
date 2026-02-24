import asyncio
import traceback
from typing import Any, Dict

from src.dependencies import init_resources, close_resources, get_graph_app

async def run():
    print("Initializing...")
    await init_resources()
    try:
        graph = get_graph_app()
        initial_state: Dict[str, Any] = {
            "user_input": "Show me the connectivity between Dallas POP and San Antonio and any related outages and tech comments.",
            "ui_context": {"selected_site": ["Dallas POP", "San Antonio"], "layer": "L2"},
            "session_id": "test_session",
            "history": [],
            "semantic_memory": [],
            "retry_count": 0,
            "max_retries": 1,
        }
        
        print("Invoking graph...")
        if hasattr(graph, "ainvoke"):
            await graph.ainvoke(initial_state)
        else:
            graph.invoke(initial_state)
            
        print("Success!")
    except Exception as e:
        print("\n=== ERROR Traceback ===")
        traceback.print_exc()
    finally:
        await close_resources()

if __name__ == "__main__":
    asyncio.run(run())
