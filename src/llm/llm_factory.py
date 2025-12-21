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

# OpenAI / vLLM-compatible
try:
    from langchain_openai import ChatOpenAI  # type: ignore
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore

# AWS Bedrock
try:
    from langchain_aws import ChatBedrock  # type: ignore
except Exception:  # pragma: no cover
    ChatBedrock = None  # type: ignore

# GCP Vertex AI
try:
    from langchain_google_vertexai import ChatVertexAI  # type: ignore
except Exception:  # pragma: no cover
    ChatVertexAI = None  # type: ignore


# --------------------------------------------------------------------------- #
# Core model factories
# --------------------------------------------------------------------------- #


def _create_openai_chat(model: str, *, temperature: float) -> BaseChatModel:
    if ChatOpenAI is None:
        raise RuntimeError(
            "ChatOpenAI is not available. Install `langchain-openai` to use the OpenAI backend."
        )
    # ChatOpenAI uses `model` and standard OPENAI_API_KEY / base URL env vars.
    return ChatOpenAI(model=model, temperature=temperature)


def _create_bedrock_chat(model_id: str, *, temperature: float) -> BaseChatModel:
    if ChatBedrock is None:
        raise RuntimeError(
            "ChatBedrock is not available. Install `langchain-aws` to use the Bedrock backend."
        )
    # Assumes AWS credentials are set via env/instance role.
    return ChatBedrock(model_id=model_id, temperature=temperature)


def _create_vertex_chat(model_name: str, *, temperature: float) -> BaseChatModel:
    if ChatVertexAI is None:
        raise RuntimeError(
            "ChatVertexAI is not available. Install `langchain-google-vertexai` to use the Vertex backend."
        )
    # Assumes GOOGLE_APPLICATION_CREDENTIALS or Workload Identity is set up.
    return ChatVertexAI(model_name=model_name, temperature=temperature)


def _create_vllm_chat(model: str, *, temperature: float) -> BaseChatModel:
    """
    vLLM backend typically exposes an OpenAI-compatible HTTP API.

    Configure:
      - OPENAI_API_BASE (or OPENAI_BASE_URL depending on client)
      - OPENAI_API_KEY (can be dummy if your gateway doesn't require it)

    Then we just reuse ChatOpenAI pointing at that base URL.
    """
    if ChatOpenAI is None:
        raise RuntimeError(
            "ChatOpenAI is not available. Install `langchain-openai` to use the vLLM backend."
        )
    # The OpenAI-compatible base URL must be set via environment variables.
    return ChatOpenAI(model=model, temperature=temperature)


# --------------------------------------------------------------------------- #
# Public model getters
# --------------------------------------------------------------------------- #


def _get_backend(settings: Settings) -> Literal["bedrock", "vertex", "openai", "vllm"]:
    return settings.llm_backend


def get_planner_model(settings: Settings | None = None) -> BaseChatModel:
    """
    Return a chat model configured for the planner agent.

    Typically a capable, reasoning-focused model (e.g., Claude Sonnet, GPT-4).
    """
    if settings is None:
        settings = get_settings()
    backend = _get_backend(settings)

    if backend == "openai":
        # Adjust model name to your needs
        return _create_openai_chat(model="gpt-4o", temperature=0.2)
    if backend == "bedrock":
        # Example Claude Sonnet on Bedrock; replace with your chosen model
        return _create_bedrock_chat(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            temperature=0.2,
        )
    if backend == "vertex":
        # Example Gemini model; adjust as needed
        return _create_vertex_chat(
            model_name="gemini-1.5-pro",
            temperature=0.2,
        )
    if backend == "vllm":
        # Example local vLLM model name
        return _create_vllm_chat(model="local-gpt-4o-equivalent", temperature=0.2)

    raise ValueError(f"Unsupported llm_backend: {backend}")


def get_validator_model(settings: Settings | None = None) -> BaseChatModel:
    """
    Return a chat model for the validator (LLM-as-judge).

    This can often be a slightly cheaper model than the planner.
    """
    if settings is None:
        settings = get_settings()
    backend = _get_backend(settings)

    if backend == "openai":
        return _create_openai_chat(model="gpt-4o-mini", temperature=0.0)
    if backend == "bedrock":
        return _create_bedrock_chat(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            temperature=0.0,
        )
    if backend == "vertex":
        return _create_vertex_chat(
            model_name="gemini-1.5-flash",
            temperature=0.0,
        )
    if backend == "vllm":
        return _create_vllm_chat(model="local-judge-model", temperature=0.0)

    raise ValueError(f"Unsupported llm_backend: {backend}")


def get_response_model(settings: Settings | None = None) -> BaseChatModel:
    """
    Return a chat model for polishing / explaining responses.

    This can often be a smaller/faster model.
    """
    if settings is None:
        settings = get_settings()
    backend = _get_backend(settings)

    if backend == "openai":
        return _create_openai_chat(model="gpt-4o-mini", temperature=0.3)
    if backend == "bedrock":
        return _create_bedrock_chat(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            temperature=0.3,
        )
    if backend == "vertex":
        return _create_vertex_chat(
            model_name="gemini-1.5-flash",
            temperature=0.3,
        )
    if backend == "vllm":
        return _create_vllm_chat(model="local-response-model", temperature=0.3)

    raise ValueError(f"Unsupported llm_backend: {backend}")


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
