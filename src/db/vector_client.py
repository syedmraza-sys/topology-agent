from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# --- Chat embeddings --------------------------------------------------------


async def upsert_chat_embedding(
    session: AsyncSession,
    *,
    session_id: str,
    message_id: int,
    embedding: Sequence[float],
    metadata: Dict[str, Any],
) -> None:
    """
    Upsert a chat message embedding into a pgvector-backed table.

    Assumes a `chat_embeddings` table with at least:
      - session_id (text)
      - message_id (bigint)
      - embedding (vector)
      - metadata (jsonb)
      - PRIMARY KEY (session_id, message_id)

    The actual DDL is up to you; this just performs an upsert.
    """
    query = text(
        """
        INSERT INTO chat_embeddings (session_id, message_id, embedding, metadata)
        VALUES (:session_id, :message_id, (:embedding)::vector, (:metadata)::jsonb)
        ON CONFLICT (session_id, message_id)
        DO UPDATE SET
          embedding = EXCLUDED.embedding,
          metadata  = EXCLUDED.metadata
        """
    )

    await session.execute(
        query,
        {
            "session_id": session_id,
            "message_id": message_id,
            # Pass as string '[0.1, 0.2, ...]' to avoid asyncpg array type confusion
            "embedding": str(list(embedding)),
            "metadata": json.dumps(metadata),
        },
    )
    await session.commit()


async def search_chat_embeddings(
    session: AsyncSession,
    *,
    session_id: str | None,
    embedding: Sequence[float],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Perform a vector similarity search over chat embeddings.

    - If session_id is provided, restrict to that session.
    - Otherwise, search globally (or adjust the WHERE clause to your needs).

    Assumes pgvector operator `<->` or `<=>` for distance/similarity.
    """
    base_query = """
        SELECT
            session_id,
            message_id,
            embedding,
            metadata,
            embedding <-> (:embedding)::vector AS distance
        FROM chat_embeddings
    """

    where_clause = ""
    params: Dict[str, Any] = {
        "embedding": str(list(embedding)),
        "limit": limit,
    }

    if session_id is not None:
        where_clause = "WHERE session_id = :session_id"
        params["session_id"] = session_id

    query = text(
        f"""
        {base_query}
        {where_clause}
        ORDER BY distance ASC
        LIMIT :limit
        """
    )
    # print("LOG: Running Vector Chat Search:", query)
    # print("LOG: Chat Params:", params)
    
    result = await session.execute(query, params)
    rows = result.mappings().all()
    return [dict(row) for row in rows]


# --- Comment embeddings -----------------------------------------------------


async def upsert_comment_embedding(
    session: AsyncSession,
    *,
    comment_id: str,
    embedding: Sequence[float],
    metadata: Dict[str, Any],
) -> None:
    """
    Upsert a comment / ticket embedding.

    Assumes a `comment_embeddings` table with at least:
      - comment_id (text)
      - embedding (vector)
      - metadata (jsonb)
      - PRIMARY KEY (comment_id)
    """
    query = text(
        """
        INSERT INTO comment_embeddings (comment_id, embedding, metadata)
        VALUES (:comment_id, (:embedding)::vector, (:metadata)::jsonb)
        ON CONFLICT (comment_id)
        DO UPDATE SET
          embedding = EXCLUDED.embedding,
          metadata  = EXCLUDED.metadata
        """
    )

    await session.execute(
        query,
        {
            "comment_id": comment_id,
            "embedding": str(list(embedding)),
            "metadata": json.dumps(metadata),
        },
    )
    await session.commit()


async def search_comment_embeddings(
    session: AsyncSession,
    *,
    embedding: Sequence[float],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Perform a vector similarity search over comment embeddings.

    Assumes pgvector operator `<->` or `<=>` for distance/similarity.
    """
    query = text(
        """
        SELECT
            comment_id,
            embedding,
            metadata,
            metadata,
            embedding <-> (:embedding)::vector AS distance
        FROM comment_embeddings
        ORDER BY distance ASC
        LIMIT :limit
        """
    )

    # print("LOG: Running Vector Comment Search:", query)

    result = await session.execute(
        query,
        {
            "embedding": str(list(embedding)),
            "limit": limit,
        },
    )
    rows = result.mappings().all()
    # print("LOG: Vector Comment Search Results:", rows) 
    return [dict(row) for row in rows]
