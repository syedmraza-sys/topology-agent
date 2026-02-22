from __future__ import annotations

from typing import Any, Literal

from ..config import Settings, get_settings
from .planner_prompt import build_planner_prompt
from .validator_prompt import build_validator_prompt
from .response_prompt import build_response_prompt

# LangChain imports are optional; guard them so the module still imports
try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.runnables import Runnable
    from langchain_core.runnables import RunnableSerializable
except Exception:  # pragma: no cover
    BaseChatModel = Any  # type: ignore
    Runnable = Any  # type: ignore
    RunnableSerializable = Any  # type: ignore


from .gateway.models import (
    create_openai_embeddings,
    create_bedrock_embeddings,
    create_vertex_embeddings,
    create_huggingface_embeddings,
)

from .gateway.client import GatewayClient

def get_comment_embedding_model(settings: Settings | None = None) -> Any:
    """
    Return an embedding model used for comment RAG.

    For now we use one embedding model per backend; adjust as needed.
    """
    if settings is None:
        settings = get_settings()
    
    # Use embedding_backend if set, otherwise fallback to llm_backend
    backend = settings.embedding_backend or settings.llm_backend

    if backend in ("openai", "vllm"):
        # vLLM usually exposes an OpenAI-compatible endpoint; we reuse OpenAIEmbeddings.
        return create_openai_embeddings(model="text-embedding-3-large")

    if backend == "bedrock":
        return create_bedrock_embeddings(model_id="amazon.titan-embed-text-v1")

    if backend == "vertex":
        return create_vertex_embeddings(model_name="textembedding-gecko")

    if backend == "huggingface":
        return create_huggingface_embeddings()

    raise ValueError(f"Unsupported backend for embeddings: {backend}")


# --------------------------------------------------------------------------- #
# Public model getters
# --------------------------------------------------------------------------- #


#def _get_backend(settings: Settings) -> Literal["bedrock", "vertex", "openai", "vllm"]:
#    return settings.llm_backend

def _get_backend(settings: Settings) -> Literal["bedrock", "vertex", "openai", "vllm", "ollama"]:
    return settings.llm_backend

def get_planner_model(settings: Settings | None = None, user_id: str = "anonymous", session_id: str = "unknown") -> BaseChatModel:
    """
    Return a chat model configured for the planner agent using the Transparent Gateway.
    """
    if settings is None:
        settings = get_settings()

    return GatewayClient.get_model(
        settings=settings,
        tier="planner",
        temperature=0.2,
        tracking_tags={
            "agent_role": "planner",
            "user_id": user_id,
            "session_id": session_id
        }
    )


def get_validator_model(settings: Settings | None = None, user_id: str = "anonymous", session_id: str = "unknown") -> BaseChatModel:
    """
    Return a chat model for the validator using the Transparent Gateway.
    """
    if settings is None:
        settings = get_settings()

    return GatewayClient.get_model(
        settings=settings,
        tier="validator",
        temperature=0.0,
        tracking_tags={
            "agent_role": "validator",
            "user_id": user_id,
            "session_id": session_id
        }
    )


def get_response_model(settings: Settings | None = None, user_id: str = "anonymous", session_id: str = "unknown") -> BaseChatModel:
    """
    Return a chat model for polishing / explaining responses using the Transparent Gateway.
    """
    if settings is None:
        settings = get_settings()

    return GatewayClient.get_model(
        settings=settings,
        tier="response",
        temperature=0.3,
        tracking_tags={
            "agent_role": "response",
            "user_id": user_id,
            "session_id": session_id
        }
    )


# --------------------------------------------------------------------------- #
# Prompt + model chains
# --------------------------------------------------------------------------- #


def get_planner_chain(settings: Settings | None = None) -> RunnableSerializable[Any, Any]:
    """
    Build a LangChain Runnable for the planner agent:

        planner_prompt | planner_model
    """
    if settings is None:
        settings = get_settings()
    prompt = build_planner_prompt()
    model = get_planner_model(settings)
    return prompt | model  # type: ignore[operator]


def get_validator_chain(settings: Settings | None = None) -> RunnableSerializable[Any, Any]:
    """
    Build a LangChain Runnable for the validator (LLM-as-judge):

        validator_prompt | validator_model
    """
    if settings is None:
        settings = get_settings()
    prompt = build_validator_prompt()
    model = get_validator_model(settings)
    return prompt | model  # type: ignore[operator]


def get_response_chain(settings: Settings | None = None) -> RunnableSerializable[Any, Any]:
    """
    Build a LangChain Runnable for response polishing / explanation:

        response_prompt | response_model
    """
    if settings is None:
        settings = get_settings()
    prompt = build_response_prompt()
    model = get_response_model(settings)
    return prompt | model  # type: ignore[operator]
