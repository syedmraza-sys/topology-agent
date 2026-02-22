from __future__ import annotations

from typing import Any, Literal
from ...config import Settings

# LangChain imports are optional; guard them so the module still imports
try:
    from langchain_core.language_models.chat_models import BaseChatModel
except Exception:  # pragma: no cover
    BaseChatModel = Any  # type: ignore

# OpenAI / vLLM-compatible
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # type: ignore
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore
    OpenAIEmbeddings = None  # type: ignore

# AWS Bedrock
try:
    from langchain_aws import ChatBedrock, BedrockEmbeddings  # type: ignore
except Exception:  # pragma: no cover
    ChatBedrock = None  # type: ignore
    BedrockEmbeddings = None  # type: ignore

# GCP Vertex AI
try:
    from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings  # type: ignore
except Exception:  # pragma: no cover
    ChatVertexAI = None  # type: ignore
    VertexAIEmbeddings = None  # type: ignore

# Ollama chat model
try:
    from langchain_ollama import ChatOllama  # type: ignore
except Exception:  # pragma: no cover
    ChatOllama = None  # type: ignore

# HuggingFace (Local)
try:
    from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
except Exception:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore
    except Exception:
        HuggingFaceEmbeddings = None


# --------------------------------------------------------------------------- #
# Core model factories
# --------------------------------------------------------------------------- #

def create_openai_chat(model: str, *, temperature: float) -> BaseChatModel:
    if ChatOpenAI is None:
        raise RuntimeError(
            "ChatOpenAI is not available. Install `langchain-openai` to use the OpenAI backend."
        )
    # ChatOpenAI uses `model` and standard OPENAI_API_KEY / base URL env vars.
    return ChatOpenAI(model=model, temperature=temperature)


def create_bedrock_chat(model_id: str, *, temperature: float) -> BaseChatModel:
    if ChatBedrock is None:
        raise RuntimeError(
            "ChatBedrock is not available. Install `langchain-aws` to use the Bedrock backend."
        )
    # Assumes AWS credentials are set via env/instance role.
    return ChatBedrock(model_id=model_id, temperature=temperature)


def create_vertex_chat(model_name: str, *, temperature: float) -> BaseChatModel:
    if ChatVertexAI is None:
        raise RuntimeError(
            "ChatVertexAI is not available. Install `langchain-google-vertexai` to use the Vertex backend."
        )
    # Assumes GOOGLE_APPLICATION_CREDENTIALS or Workload Identity is set up.
    return ChatVertexAI(model_name=model_name, temperature=temperature)


def create_vllm_chat(model: str, *, temperature: float) -> BaseChatModel:
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


def create_ollama_chat(
    settings: Settings,
    *,
    temperature: float,
) -> BaseChatModel:
    """
    Create a ChatOllama model using a local Ollama service.
    """
    if ChatOllama is None:
        raise RuntimeError(
            "ChatOllama is not available. Install `langchain-community` to use the Ollama backend."
        )

    kwargs = {
        "base_url": settings.ollama_base_url,
        "model": settings.ollama_model,
        "temperature": temperature if settings.ollama_temperature is None else settings.ollama_temperature,
    }

    if settings.ollama_num_ctx is not None:
        kwargs["num_ctx"] = settings.ollama_num_ctx
    if settings.ollama_num_predict is not None:
        kwargs["num_predict"] = settings.ollama_num_predict
    if settings.ollama_num_gpu is not None:
        kwargs["num_gpu"] = settings.ollama_num_gpu
    if settings.ollama_num_thread is not None:
        kwargs["num_thread"] = settings.ollama_num_thread
    if settings.ollama_top_k is not None:
        kwargs["top_k"] = settings.ollama_top_k
    if settings.ollama_top_p is not None:
        kwargs["top_p"] = settings.ollama_top_p
    if settings.ollama_repeat_penalty is not None:
        kwargs["repeat_penalty"] = settings.ollama_repeat_penalty
    if settings.ollama_keep_alive is not None:
        kwargs["keep_alive"] = settings.ollama_keep_alive

    return ChatOllama(**kwargs)


# --------------------------------------------------------------------------- #
# Embedding model factories
# --------------------------------------------------------------------------- #

def create_openai_embeddings(model: str = "text-embedding-3-large") -> Any:
    if OpenAIEmbeddings is None:
        raise RuntimeError(
            "OpenAIEmbeddings is not available. Install `langchain-openai` to use the OpenAI embedding backend."
        )
    return OpenAIEmbeddings(model=model)


def create_bedrock_embeddings(
    model_id: str = "amazon.titan-embed-text-v1",
) -> Any:
    if BedrockEmbeddings is None:
        raise RuntimeError(
            "BedrockEmbeddings is not available. Install `langchain-aws` to use the Bedrock embedding backend."
        )
    return BedrockEmbeddings(model_id=model_id)


def create_vertex_embeddings(
    model_name: str = "textembedding-gecko",
) -> Any:
    if VertexAIEmbeddings is None:
        raise RuntimeError(
            "VertexAIEmbeddings is not available. Install `langchain-google-vertexai` to use the Vertex embedding backend."
        )
    return VertexAIEmbeddings(model_name=model_name)


def create_huggingface_embeddings(
    model_name: str = "sentence-transformers/all-mpnet-base-v2",
) -> Any:
    if HuggingFaceEmbeddings is None:
        raise RuntimeError(
            "HuggingFaceEmbeddings is not available. Install `langchain-huggingface` (and `sentence-transformers`) to use the HuggingFace embedding backend."
        )
    return HuggingFaceEmbeddings(model_name=model_name)
