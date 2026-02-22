from typing import Any, Dict, Literal
import logging
from .storage import FileUsageStore
from .budget import UsageTrackingCallbackHandler
from .models import (
    create_openai_chat,
    create_bedrock_chat,
    create_vertex_chat,
    create_vllm_chat,
    create_ollama_chat,
)
from ...config import Settings

logger = logging.getLogger(__name__)

# Singleton storage
usage_store = FileUsageStore()

class GatewayClient:
    """
    Transparent Gateway Interface for fetching LLM models.
    Enforces budgets, routes to fallbacks, and injects usage-tracking callbacks.
    """

    @classmethod
    def get_model(
        cls,
        settings: Settings,
        tier: Literal["planner", "validator", "response"],
        temperature: float,
        tracking_tags: Dict[str, str],
    ) -> Any:
        
        user_id = tracking_tags.get("user_id", "anonymous")
        agent_role = tracking_tags.get("agent_role", tier)
        
        # 1. Budget Verification
        global_spend = usage_store.get_global_cost()
        user_spend = usage_store.get_user_cost(user_id)
        
        backend = settings.llm_backend
        
        limit_breached = False
        if global_spend >= settings.global_llm_budget:
            logger.warning(f"GLOBAL budget breached! Spent: ${global_spend:.2f} Limit: ${settings.global_llm_budget:.2f}")
            limit_breached = True
        elif user_spend >= settings.user_llm_budget:
            logger.warning(f"USER {user_id} budget breached! Spent: ${user_spend:.2f} Limit: ${settings.user_llm_budget:.2f}")
            limit_breached = True
            
        # 2. Degradation Action
        if limit_breached:
            logger.warning(f"Degrading backend from {backend} to {settings.fallback_backend}")
            backend = settings.fallback_backend
            
        # 3. Model Generation
        model = cls._create_model_from_tier(backend, tier, settings, temperature)
        
        # 4. Instrumentation (Inject Usage Tracking Callback)
        callback = UsageTrackingCallbackHandler(storage=usage_store, user_id=user_id, agent_role=agent_role)
        
        # We must return a bound model with the callback attached
        return model.with_config({"callbacks": [callback], "tags": [tier, user_id]})
    
    @staticmethod
    def _create_model_from_tier(
        backend: str, tier: str, settings: Settings, temperature: float
    ) -> Any:
        # Define tier-specific model names here internally so it isolates logic away from factory
        if backend == "openai":
            if tier == "planner":
                return create_openai_chat(model="gpt-4o", temperature=temperature)
            else:
                return create_openai_chat(model="gpt-4o-mini", temperature=temperature)
                
        elif backend == "bedrock":
            if tier == "planner":
                return create_bedrock_chat(model_id="anthropic.claude-3-sonnet-20240229-v1:0", temperature=temperature)
            else:
                return create_bedrock_chat(model_id="anthropic.claude-3-haiku-20240307-v1:0", temperature=temperature)
                
        elif backend == "vertex":
            if tier == "planner":
                return create_vertex_chat(model_name="gemini-1.5-pro", temperature=temperature)
            else:
                return create_vertex_chat(model_name="gemini-1.5-flash", temperature=temperature)
                
        elif backend == "vllm":
            if tier == "planner":
                return create_vllm_chat(model="local-gpt-4o-equivalent", temperature=temperature)
            else:
                return create_vllm_chat(model="local-judge-model", temperature=temperature)
                
        elif backend == "ollama":
            return create_ollama_chat(settings, temperature=temperature)
            
        raise ValueError(f"Gateway unsupported backend: {backend}")
