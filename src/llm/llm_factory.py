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

# llama.cpp chat model (local GGUF)
try:
    from langchain_community.chat_models import ChatLlamaCpp  # type: ignore
except Exception:  # pragma: no cover
    ChatLlamaCpp = None  # type: ignore


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

def _create_llamacpp_chat(
    settings: Settings,
    *,
    temperature: float,
) -> BaseChatModel:
    """
    Create a ChatLlamaCpp model using a local GGUF file, e.g.
    mistral-7b-instruct-v0.2.Q4_K_M.gguf
    """
    if ChatLlamaCpp is None:
        raise RuntimeError(
            "ChatLlamaCpp is not available. Install `llama-cpp-python` "
            "and `langchain-community` to use the llama.cpp backend."
        )

    if not settings.llama_model_path:
        raise RuntimeError(
            "llama_model_path is not configured. "
            "Set TOPOLOGY_AGENT_LLAMA_MODEL_PATH to your GGUF file path."
        )

    return ChatLlamaCpp(
        model_path=settings.llama_model_path,
        temperature=temperature,
        n_ctx=settings.llama_n_ctx,
        n_gpu_layers=settings.llama_n_gpu_layers,
        n_threads=settings.llama_n_threads,
        verbose=False,
    )


# --------------------------------------------------------------------------- #
# Embedding model factories
# --------------------------------------------------------------------------- #


def _create_openai_embeddings(model: str = "text-embedding-3-large") -> Any:
    if OpenAIEmbeddings is None:
        raise RuntimeError(
            "OpenAIEmbeddings is not available. Install `langchain-openai` to use the OpenAI embedding backend."
        )
    return OpenAIEmbeddings(model=model)


def _create_bedrock_embeddings(
    model_id: str = "amazon.titan-embed-text-v1",
) -> Any:
    if BedrockEmbeddings is None:
        raise RuntimeError(
            "BedrockEmbeddings is not available. Install `langchain-aws` to use the Bedrock embedding backend."
        )
    return BedrockEmbeddings(model_id=model_id)


def _create_vertex_embeddings(
    model_name: str = "textembedding-gecko",
) -> Any:
    if VertexAIEmbeddings is None:
        raise RuntimeError(
            "VertexAIEmbeddings is not available. Install `langchain-google-vertexai` to use the Vertex embedding backend."
        )
    return VertexAIEmbeddings(model_name=model_name)


def _create_huggingface_embeddings(
    model_name: str = "sentence-transformers/all-mpnet-base-v2",
) -> Any:
    if HuggingFaceEmbeddings is None:
        raise RuntimeError(
            "HuggingFaceEmbeddings is not available. Install `langchain-huggingface` (and `sentence-transformers`) to use the HuggingFace embedding backend."
        )
    return HuggingFaceEmbeddings(model_name=model_name)


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
        return _create_openai_embeddings(model="text-embedding-3-large")

    if backend == "bedrock":
        return _create_bedrock_embeddings(model_id="amazon.titan-embed-text-v1")

    if backend == "vertex":
        return _create_vertex_embeddings(model_name="textembedding-gecko")

    if backend == "huggingface":
        return _create_huggingface_embeddings()

    raise ValueError(f"Unsupported backend for embeddings: {backend}")


# --------------------------------------------------------------------------- #
# Public model getters
# --------------------------------------------------------------------------- #


#def _get_backend(settings: Settings) -> Literal["bedrock", "vertex", "openai", "vllm"]:
#    return settings.llm_backend

def _get_backend(settings: Settings) -> Literal["bedrock", "vertex", "openai", "vllm", "llamacpp"]:
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

    if backend == "llamacpp":
        # Mistral-7B-Instruct via llama.cpp
        return _create_llamacpp_chat(settings, temperature=0.2)
    
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

    if backend == "llamacpp":
        return _create_llamacpp_chat(settings, temperature=0.0)

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

    if backend == "llamacpp":
        return _create_llamacpp_chat(settings, temperature=0.3)

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
