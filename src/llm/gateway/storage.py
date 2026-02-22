import json
import logging
from pathlib import Path
from typing import Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class UsageStore(ABC):
    @abstractmethod
    def add_cost(self, user_id: str, cost: float, model_name: str = "unknown", prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        pass

    @abstractmethod
    def log_call(self, log_entry: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_user_cost(self, user_id: str) -> float:
        pass

    @abstractmethod
    def get_global_cost(self) -> float:
        pass


class FileUsageStore(UsageStore):
    def __init__(self, filepath: str = ".llm_usage.json", log_filepath: str = ".llm_call_logs.jsonl"):
        self.filepath = Path(filepath)
        self.log_filepath = Path(log_filepath)
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.filepath.exists():
            self._save({"global": 0.0, "users": {}, "providers": {}})

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"global": 0.0, "users": {}, "providers": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)

    def add_cost(self, user_id: str, cost: float, model_name: str = "unknown", prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        if cost <= 0 and prompt_tokens == 0 and completion_tokens == 0:
            return

        data = self._load()
        
        # Update global
        data["global"] = data.get("global", 0.0) + cost
        
        # Update user
        if user_id:
            users = data.get("users", {})
            users[user_id] = users.get(user_id, 0.0) + cost
            data["users"] = users

        # Update per-LLM model stats
        providers = data.get("providers", {})
        provider_data = providers.get(model_name, {"cost": 0.0, "prompt_tokens": 0, "completion_tokens": 0})
        provider_data["cost"] += cost
        provider_data["prompt_tokens"] += prompt_tokens
        provider_data["completion_tokens"] += completion_tokens
        providers[model_name] = provider_data
        data["providers"] = providers

        self._save(data)
        logger.debug(f"Added ${cost:.4f} to User: {user_id}, Model: {model_name}. Global total: ${data['global']:.4f}")

    def get_user_cost(self, user_id: str) -> float:
        data = self._load()
        return data.get("users", {}).get(user_id, 0.0)

    def get_global_cost(self) -> float:
        data = self._load()
        return data.get("global", 0.0)

    def log_call(self, log_entry: Dict[str, Any]) -> None:
        try:
            with open(self.log_filepath, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except IOError as e:
            logger.error(f"Failed to write call log: {e}")
