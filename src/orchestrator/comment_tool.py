from __future__ import annotations

import collections
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from .state_types import TopologyState
from ..config import get_settings
from ..dependencies import get_session_maker
from ..db import vector_client
from ..llm.llm_factory import get_comment_embedding_model

# Load model globally to keep it warm
_cross_encoder = None

def get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)
    return _cross_encoder


async def run_comment_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Query pgvector for user comments / tickets relevant to this query.
    Uses a Three-Stage Reranking Pipeline:
      1. Vector Search (Top 50 candidate generation)
      2. BM25 + RRF (Reciprocal Rank Fusion) for exact keyword matches (Top 15)
      3. CrossEncoder Transformer (Final Top 5 Rerank)
    """
    settings = get_settings()

    # Extract params from the scheduled plan step
    plan = state.get("plan", {})
    steps = plan.get("steps", [])
    
    params = {}
    for step in steps:
        if step.get("tool") in ["comment_tool", "comments_search_tool"]:
            params = step.get("params", {})
            break

    user_input: str = state.get("user_input", "") or ""
    ui_context: Dict[str, Any] = state.get("ui_context", {}) or {}

    # Pluck from params
    query_text = params.get("query_text")
    site_names = params.get("site_names", [])
    device_ids = params.get("device_ids", [])
    circuit_ids = params.get("circuit_ids", [])
    top_k_param = params.get("top_k")
    
    # Resolve refs
    if isinstance(device_ids, str) and device_ids.startswith("$ref"):
        topology_data = state.get("topology_data") or {}
        resolved_devices = set()
        for path in topology_data.get("paths", []):
            resolved_devices.update(path.get("hops", []))
        device_ids = list(resolved_devices)

    if isinstance(circuit_ids, str) and circuit_ids.startswith("$ref"):
        inventory_data = state.get("inventory_data") or {}
        circuit_ids = [c.get("circuit_id") for c in inventory_data.get("circuits", []) if c.get("circuit_id")]

    # Ultimate fallback strategy for query search text
    search_text = query_text or user_input
    if not search_text.strip():
        print("DEBUG: comment_tool skipping due to empty input")
        return {
            "comments": [],
            "metadata": {
                "source": "comment_tool",
                "reason": "empty search_text",
            },
        }

    # Decide on final K
    final_top_k = top_k_param if top_k_param is not None else settings.comment_rag_top_k

    # --- 1) Embed the query & Search pgvector (Candidate Generation) ---
    embed_model = get_comment_embedding_model(settings)
    embedding: List[float] = embed_model.embed_query(search_text)

    # Ask for a broad set of candidates (e.g. 50)
    BROAD_K = 50
    SessionLocal = get_session_maker()
    async with SessionLocal() as session:  # type: AsyncSession
        rows = await vector_client.search_comment_embeddings(
            session,
            embedding=embedding,
            limit=BROAD_K,
        )

    if not rows:
        return {
            "comments": [],
            "metadata": {"source": "comment_rag_pgvector", "query_text": search_text, "num_results": 0}
        }

    # Format documents
    docs = []
    for i, row in enumerate(rows):
        metadata = row.get("metadata") or {}
        # We index using i to preserve the pgvector ranking order
        docs.append({
            "id": row.get("comment_id"),
            "text": metadata.get("text", ""),
            "metadata": metadata,
            "vector_rank": i + 1,  # 1-indexed rank
            "vector_distance": float(row.get("distance", 0.0))
        })

    # --- 2) BM25 Keyword Scoring & Reciprocal Rank Fusion (RRF) ---
    # Tokenize the documents for BM25
    tokenized_corpus = [doc["text"].lower().split() for doc in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    
    tokenized_query = search_text.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    
    # Sort docs by BM25 score to get BM25 ranks
    # enumerate gives us the original index to map back
    scored_indices = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)
    
    # Assign BM25 ranks
    bm25_ranks = {}
    for rank, (original_idx, score) in enumerate(scored_indices):
        bm25_ranks[original_idx] = rank + 1 # 1-indexed

    # Calculate RRF Score for each document
    # RRF = 1 / (k + rank_1) + 1 / (k + rank_2) (where k is usually 60)
    K = 60
    for i, doc in enumerate(docs):
        doc["bm25_rank"] = bm25_ranks[i]
        doc["rrf_score"] = (1.0 / (K + doc["vector_rank"])) + (1.0 / (K + doc["bm25_rank"]))

    # Sort by RRF score and keep Top 15 candidates
    RRF_K = 15
    docs.sort(key=lambda x: x["rrf_score"], reverse=True)
    rrf_candidates = docs[:RRF_K]

    # --- 3) Cross-Encoder Reranking ---
    # Prepare input for the cross-encoder: [[query, doc_text], [query, doc_text], ...]
    encoder = get_cross_encoder()
    ce_inputs = [[search_text, c["text"]] for c in rrf_candidates]
    ce_scores = encoder.predict(ce_inputs)

    # Attach scores and sort
    for i, score in enumerate(ce_scores):
        rrf_candidates[i]["cross_encoder_score"] = float(score)

    rrf_candidates.sort(key=lambda x: x["cross_encoder_score"], reverse=True)

    # Final Top K
    final_docs = rrf_candidates[:final_top_k]

    comments = []
    for d in final_docs:
        comments.append({
            "comment_id": d["id"],
            "distance": d["vector_distance"], # Returning original vector distance for legacy compatibility
            "cross_encoder_score": d["cross_encoder_score"],
            "rrf_score": d["rrf_score"],
            **d["metadata"]
        })

    return {
        "comments": comments,
        "metadata": {
            "source": "comment_rag_pgvector_reranked",
            "query_text": search_text,
            "top_k": final_top_k,
            "num_candidates_vector": len(docs),
            "num_candidates_rrf": len(rrf_candidates),
            "num_results": len(comments),
            "elements_checked": {
                "sites": len(site_names),
                "devices": len(device_ids),
                "circuits": len(circuit_ids)
            }
        },
    }
