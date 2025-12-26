from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from .state_types import TopologyState
from ..config import get_settings
from ..dependencies import get_session_maker
from ..db import vector_client
from ..llm.llm_factory import get_comment_embedding_model


async def run_comment_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Query pgvector for user comments / tickets relevant to this query.

    Flow:
      - Build a search query text from user_input (and possibly ui_context).
      - Embed that text using the configured embedding backend.
      - Use pgvector (via vector_client.search_comment_embeddings) to find
        the top-K most similar comments.
      - Return a structured payload suitable for the orchestrator and UI.

    Assumes a Postgres table `comment_embeddings` with columns:
      - comment_id (text)
      - embedding (vector)
      - metadata (jsonb)
    and that it is populated by an offline ingestion process.
    """
    settings = get_settings()

    user_input: str = state.get("user_input", "") or ""
    ui_context: Dict[str, Any] = state.get("ui_context", {}) or {}

    # print(f"DEBUG: comment_tool input='{user_input}'")

    if not user_input.strip():
        print("DEBUG: comment_tool skipping due to empty input")
        return {
            "comments": [],
            "metadata": {
                "source": "comment_tool",
                "reason": "empty user_input",
            },
        }

    # --- 1) Build the semantic search text -------------------------------

    # Simple strategy: just use the user_input for now.
    # Later you can augment with site IDs, layer, etc.
    search_text = user_input

    # --- 2) Embed the query ----------------------------------------------

    embed_model = get_comment_embedding_model(settings)
    
    # print(f"DEBUG: comment_tool embedding text='{search_text}' with model={type(embed_model)}")
    
    # LangChain embeddings are typically synchronous; we call them directly.
    # In a highly concurrent environment you may want to offload this to a
    # thread pool or a worker.
    embedding: List[float] = embed_model.embed_query(search_text)
    
    # print(f"DEBUG: comment_tool generated embedding len={len(embedding)}")

    # --- 3) Search pgvector ----------------------------------------------

    SessionLocal = get_session_maker()
    async with SessionLocal() as session:  # type: AsyncSession
        rows = await vector_client.search_comment_embeddings(
            session,
            embedding=embedding,
            limit=settings.comment_rag_top_k,
        )
        print(f"DEBUG: comment_tool db search returned {len(rows)} rows")

    # rows: [ {comment_id, embedding, metadata, distance}, ... ]
    comments: List[Dict[str, Any]] = []
    for row in rows:
        metadata = row.get("metadata") or {}
        comments.append(
            {
                "comment_id": row.get("comment_id"),
                "distance": float(row.get("distance", 0.0)),
                # Merge metadata fields directly for convenience in the UI.
                **metadata,
            }
        )

    # print(f"DEBUG: comment_tool comments={comments}")

    return {
        "comments": comments,
        "metadata": {
            "source": "comment_rag_pgvector",
            "query_text": search_text,
            "top_k": settings.comment_rag_top_k,
            "num_results": len(comments),
        },
    }
