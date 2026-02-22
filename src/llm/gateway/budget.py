import logging
from typing import Any, Dict, List
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from .storage import UsageStore
from datetime import datetime, timezone
from ...config import get_settings

logger = logging.getLogger(__name__)

# Approximate mapping for a few common models (cost per 1k tokens)
COST_MAPPING = {
    # OpenAI
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    
    # Bedrock Example 
    "anthropic.claude-3-sonnet-20240229-v1:0": {"input": 0.003, "output": 0.015},
    "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00025, "output": 0.00125},

    # local Ollama / vLLM (always zero)
    "mistral": {"input": 0.0, "output": 0.0},
    "mistral:7b-instruct-v0.3-q4_K_M": {"input": 0.0, "output": 0.0},
    "local-gpt-4o-equivalent": {"input": 0.0, "output": 0.0},
    "local-judge-model": {"input": 0.0, "output": 0.0},
    "local-response-model": {"input": 0.0, "output": 0.0}
}

def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    # Attempt to find the model explicitly
    # if not exact, fallback to a smart guess based on prefix
    pricing = COST_MAPPING.get(model_name)
    
    if not pricing:
        for known_model, rates in COST_MAPPING.items():
            if known_model in model_name:
                pricing = rates
                break
    
    # If totally unknown, treat as 0 or default unknown rate.
    if not pricing:
        logger.warning(f"Cost mapping not found for {model_name}. Recording $0 cost.")
        return 0.0
        
    in_cost = (prompt_tokens / 1000.0) * pricing["input"]
    out_cost = (completion_tokens / 1000.0) * pricing["output"]
    return in_cost + out_cost


class UsageTrackingCallbackHandler(BaseCallbackHandler):
    """
    Callback handler to track token usage and write it to the provided UsageStore.
    """

    def __init__(self, storage: UsageStore, user_id: str, agent_role: str = "unknown"):
        self.storage = storage
        self.user_id = user_id
        self.agent_role = agent_role

    def on_llm_end(self, response: Any, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> Any:
        try:
            prompt_tokens = 0
            completion_tokens = 0
            model_name = ""

            # 1. Try legacy llm_output format
            llm_output = response.llm_output or {}
            token_usage = llm_output.get("token_usage", {})
            model_name = llm_output.get("model_name", "")

            if token_usage:
                prompt_tokens = token_usage.get("prompt_tokens", 0)
                completion_tokens = token_usage.get("completion_tokens", 0)

            # 2. Try modern LangChain AIMessage metadata format
            if (prompt_tokens == 0 and completion_tokens == 0) or not model_name:
                for gen_list in response.generations:
                    for gen in gen_list:
                        msg = getattr(gen, "message", None)
                        if msg:
                            usage_meta = getattr(msg, "usage_metadata", {}) or {}
                            if usage_meta:
                                prompt_tokens = usage_meta.get("input_tokens", prompt_tokens)
                                completion_tokens = usage_meta.get("output_tokens", completion_tokens)
                            
                            resp_meta = getattr(msg, "response_metadata", {}) or {}
                            if resp_meta and not model_name:
                                model_name = resp_meta.get("model", resp_meta.get("model_name", model_name))

            # 3. Final fallback for model_name
            if not model_name: 
                if "model" in kwargs:
                    model_name = kwargs["model"]
                else:
                    model_name = "unknown-model"

            total_cost = calculate_cost(model_name, prompt_tokens, completion_tokens)
            
            self.storage.add_cost(
                user_id=self.user_id, 
                cost=total_cost, 
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )

            # Record a structured per-call log
            try:
                settings = get_settings()
                app_name = settings.app_name
            except Exception:
                app_name = "unknown-app"

            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "application": app_name,
                "user": self.user_id,
                "node_name": self.agent_role,
                "llm_name": model_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": total_cost,
                "run_id": str(run_id)
            }
            self.storage.log_call(log_entry)

        except Exception as e:
            logger.error(f"Error handling usage callback: {str(e)}")
