from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from ..config import Settings
from ..dependencies import (
    get_context_logger,
    get_graph_app,
    get_settings_dep,
)
from ..orchestrator.domain_metrics import TOPOLOGY_QUERY_SUCCESS, TOPOLOGY_QUERY_FAILURE

try:
    from langgraph.graph import CompiledGraph  # type: ignore
except Exception:  # pragma: no cover
    CompiledGraph = Any  # type: ignore

router = APIRouter(tags=["topology"], prefix="/topology")


# ---------- Pydantic Schemas ----------


class TopologyUIContext(BaseModel):
    """
    Optional UI context sent by the frontend, e.g. selected sites, layers, filters.
    This is deliberately flexible.
    """

    selected_sites: Optional[List[str]] = None
    layer: Optional[str] = Field(default=None, description="e.g. L2, L3")
    time_range: Optional[Dict[str, Any]] = None  # {"from": "...", "to": "..."}
    filters: Dict[str, Any] = Field(default_factory=dict)


class TopologyQueryRequest(BaseModel):
    """
    Request body for /topology/query.
    """

    query: str = Field(..., description="Natural language topology / inventory question.")
    ui_context: Optional[TopologyUIContext] = Field(
        default=None,
        description="Optional UI context (selected sites, filters, etc.).",
    )
    session_id: Optional[UUID] = Field(
        default=None,
        description="Optional chat/session identifier for continuity & memory.",
    )


class TopologyPath(BaseModel):
    """
    Example representation of a computed path.
    Adjust fields to match your domain model.
    """

    src_site: str
    dst_site: str
    layer: str
    hops: List[str] = Field(
        default_factory=list,
        description="Ordered list of nodes/links representing the path.",
    )


class TopologyImpactSummary(BaseModel):
    """
    Summary of impact for the UI.
    """

    total_circuits: int = 0
    impacted_circuits: int = 0
    impacted_customers: int = 0
    notes: Optional[str] = None


class TopologyResponse(BaseModel):
    """
    High-level response returned to the UI for a topology query.
    """

    request_id: UUID = Field(..., description="Server-side request identifier.")
    session_id: Optional[UUID] = Field(
        default=None, description="Chat/session identifier, if used."
    )
    view_type: str = Field(
        "path_view",
        description="Logical view type for the UI (e.g. path_view, site_view, circuit_view).",
    )
    summary: TopologyImpactSummary
    paths: List[TopologyPath] = Field(default_factory=list)
    circuits: List[Dict[str, Any]] = Field(
        default_factory=list, description="Enriched circuit objects for tabular UI."
    )
    comments: List[Dict[str, Any]] = Field(
        default_factory=list, description="Relevant comments fetched via RAG."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal issues or degradation notices.",
    )
    partial: bool = Field(
        False,
        description="True if response may be incomplete due to tool/LLM/DB issues.",
    )
    raw_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional subset of the orchestrator state for debugging.",
    )


# ---------- Endpoint ----------


@router.post(
    "/query",
    response_model=TopologyResponse,
    status_code=status.HTTP_200_OK,
)
async def topology_query(
    payload: TopologyQueryRequest,
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    logger=Depends(get_context_logger),
    graph_app: CompiledGraph = Depends(get_graph_app),
) -> TopologyResponse:
    """
    Entrypoint for topology/inventory queries.

    - Builds an initial TopologyState from the request.
    - Invokes the LangGraph graph.
    - Normalizes the result into TopologyResponse.
    """
    # 1. Retrieve request_id from middleware (or gen new if missing)
    if hasattr(request.state, "request_id"):
        request_id = request.state.request_id
    else:
        # Fallback if middleware not active
        request_id = str(uuid4())

    logger = logger.bind(request_id=str(request_id))
    logger.info("topology_query_received", query=payload.query)

    # 2. Build initial state including request_id
    initial_state: Dict[str, Any] = {
        "user_input": payload.query,
        "ui_context": payload.ui_context.model_dump() if payload.ui_context else {},
        "session_id": str(payload.session_id) if payload.session_id else None,
        "request_id": str(request_id),
        "history": [],
        "semantic_memory": [],
        "retry_count": 0,
        "max_retries": 1,
    }

    # 3. Invoke LangGraph with metadata for LangSmith
    config = {
        "configurable": {"thread_id": str(payload.session_id) if payload.session_id else str(request_id)},
        "metadata": {
            "request_id": str(request_id),
            "session_id": str(payload.session_id) if payload.session_id else None,
            "source": "api",
        },
    }

    try:
        if hasattr(graph_app, "ainvoke"):
            print("LOG: Using async graph_app")
            result_state = await graph_app.ainvoke(initial_state, config=config)  # type: ignore[attr-defined]
            TOPOLOGY_QUERY_SUCCESS.inc()
        else:
            print("LOG: Using sync graph_app")
            result_state = graph_app.invoke(initial_state, config=config)  # type: ignore[call-arg]
            TOPOLOGY_QUERY_SUCCESS.inc()
    except Exception as exc:
        logger.error(
            "topology_query_failed",
            error=str(exc),
            exc_info=True,
        )
        TOPOLOGY_QUERY_FAILURE.inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process topology query.",
        ) from exc

    logger.info(
        "topology_query_completed",
        query=payload.query,
        partial=bool(result_state.get("partial")),
    )

    # Normalize orchestrator state into TopologyResponse.
    # These keys should be written by your correlate_and_validate / response node.
    ui_payload = result_state.get("ui_response", {}) or {}

    summary = TopologyImpactSummary(
        total_circuits=ui_payload.get("summary", {}).get("total_circuits", 0),
        impacted_circuits=ui_payload.get("summary", {}).get("impacted_circuits", 0),
        impacted_customers=ui_payload.get("summary", {}).get("impacted_customers", 0),
        notes=ui_payload.get("summary", {}).get("notes"),
    )

    paths = [
        TopologyPath(**p) for p in ui_payload.get("paths", [])
    ] if ui_payload.get("paths") else []

    circuits = ui_payload.get("circuits", []) or []
    comments = ui_payload.get("comments", []) or []
    warnings = ui_payload.get("warnings", []) or []
    partial = bool(ui_payload.get("partial") or result_state.get("partial"))

    return TopologyResponse(
        request_id=request_id,
        session_id=payload.session_id,
        view_type=ui_payload.get("view_type", "path_view"),
        summary=summary,
        paths=paths,
        circuits=circuits,
        comments=comments,
        warnings=warnings,
        partial=partial,
        raw_state=ui_payload.get("debug_state"),
    )
