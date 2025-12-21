from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..dependencies import (
    get_context_logger,
    get_db_session,
    get_graph_app,
    get_settings_dep,
)

try:
    from langgraph.graph import CompiledGraph  # type: ignore
except Exception:  # pragma: no cover
    CompiledGraph = Any  # type: ignore

router = APIRouter(tags=["chat"], prefix="/chat")


# ---------- Schemas ----------


class ChatMessage(BaseModel):
    id: Optional[int] = None
    session_id: Optional[UUID] = None
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatTurnRequest(BaseModel):
    session_id: Optional[UUID] = Field(
        default=None,
        description="Existing session id, or null to start a new session.",
    )
    message: ChatMessage = Field(
        ..., description="User message for this turn (role=user)."
    )
    ui_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional UI context to pass into the topology agent.",
    )


class ChatTurnResponse(BaseModel):
    session_id: UUID
    messages: List[ChatMessage]
    topology_response: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional topology UI payload if this turn triggered the topology agent.",
    )


class ChatSessionSummary(BaseModel):
    session_id: UUID
    started_at: datetime
    last_message_at: datetime
    title: Optional[str] = None
    message_count: int


# ---------- Helper stubs (to be wired to db.chat later) ----------


async def _create_or_get_session_id(
    db: AsyncSession,
    user_id: str | None,
    session_id: Optional[UUID],
) -> UUID:
    """
    Placeholder for a real DB-backed chat_sessions table.

    For now, if session_id is provided, assume it's valid. If not, generate a new UUID.
    """
    # TODO: integrate with src/db/* when you add chat models.
    return session_id or uuid4()


async def _store_message(
    db: AsyncSession,
    chat_message: ChatMessage,
) -> ChatMessage:
    """
    Placeholder: store the message in DB and return with id set.
    """
    # TODO: insert into chat_messages table and return ID.
    # For now, just fake an ID.
    chat_message.id = chat_message.id or int(datetime.now().timestamp())
    return chat_message


async def _load_recent_messages(
    db: AsyncSession,
    session_id: UUID,
    limit: int = 20,
) -> List[ChatMessage]:
    """
    Placeholder: fetch last N messages for a session.
    """
    # TODO: implement using chat_messages table ordered by created_at.
    return []


async def _list_sessions(
    db: AsyncSession,
    user_id: str | None,
    limit: int = 50,
) -> List[ChatSessionSummary]:
    """
    Placeholder: list chat sessions for a user.
    """
    # TODO: implement using chat_sessions table.
    return []


# ---------- Endpoints ----------


@router.post(
    "/turn",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_200_OK,
)
async def chat_turn(
    payload: ChatTurnRequest,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dep),
    logger=Depends(get_context_logger),
    graph_app: CompiledGraph = Depends(get_graph_app),
) -> ChatTurnResponse:
    """
    Handle a single chat turn:

    - Ensure there's a session_id (create or reuse).
    - Store the user message.
    - Call the topology agent (LangGraph) if appropriate.
    - Store the assistant message.
    - Return recent messages + optional topology response payload.
    """
    # NOTE: in a real app, user_id comes from auth (e.g. JWT claims).
    user_id: str | None = None

    session_id = await _create_or_get_session_id(db, user_id, payload.session_id)
    logger = logger.bind(session_id=str(session_id))

    if payload.message.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ChatTurnRequest.message.role must be 'user'.",
        )

    user_msg = payload.message.copy(update={"session_id": session_id})
    user_msg = await _store_message(db, user_msg)
    logger.info("chat_user_message_stored", message_id=user_msg.id)

    # Decide if this message should trigger the topology agent.
    # For now, simple heuristic: everything goes through the agent.
    initial_state: Dict[str, Any] = {
        "user_input": user_msg.content,
        "ui_context": payload.ui_context,
        "session_id": str(session_id),
        "history": [],           # could be populated by a memory node
        "semantic_memory": [],   # could be a memory tool
        "retry_count": 0,
        "max_retries": 1,
    }

    topology_ui_response: Optional[Dict[str, Any]] = None
    assistant_text = "OK."

    try:
        if hasattr(graph_app, "ainvoke"):
            result_state = await graph_app.ainvoke(initial_state)  # type: ignore[attr-defined]
        else:
            result_state = graph_app.invoke(initial_state)  # type: ignore[call-arg]

        ui_payload = result_state.get("ui_response", {}) or {}
        topology_ui_response = ui_payload
        assistant_text = ui_payload.get(
            "natural_language_summary",
            "Here is the topology result.",
        )
        logger.info("chat_topology_agent_completed", partial=bool(ui_payload.get("partial")))
    except Exception as exc:
        logger.error("chat_topology_agent_failed", error=str(exc), exc_info=True)
        assistant_text = "Sorry, I couldn’t process that topology query."
        topology_ui_response = None

    # Store assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_text,
    )
    assistant_msg = await _store_message(db, assistant_msg)
    logger.info("chat_assistant_message_stored", message_id=assistant_msg.id)

    # Load recent messages for context (UI can also load as needed)
    recent_messages = await _load_recent_messages(db, session_id=session_id, limit=20)
    # Ensure we include the current turn if _load_recent_messages() is not implemented yet
    if not recent_messages:
        recent_messages = [user_msg, assistant_msg]

    return ChatTurnResponse(
        session_id=session_id,
        messages=recent_messages,
        topology_response=topology_ui_response,
    )


@router.get(
    "/sessions",
    response_model=List[ChatSessionSummary],
    status_code=status.HTTP_200_OK,
)
async def list_chat_sessions(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
    logger=Depends(get_context_logger),
) -> List[ChatSessionSummary]:
    """
    List chat sessions for the current user.

    This uses stub helpers for now; wire it to your chat_sessions table later.
    """
    user_id: str | None = None  # TODO: derive from auth
    logger.info("chat_sessions_list_requested", limit=limit)
    sessions = await _list_sessions(db, user_id=user_id, limit=limit)
    return sessions
