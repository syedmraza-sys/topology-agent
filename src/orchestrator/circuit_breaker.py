from __future__ import annotations

import time
import threading
from typing import Dict, Set
import structlog

logger = structlog.get_logger("orchestrator.circuit_breaker")

class CircuitBreaker:
    """
    Very simple in-memory circuit breaker for tools.
    In a real production environment with multiple workers, 
    this state should be persisted in Redis.
    """
    def __init__(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: int = 60
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        # State: tool_name -> count
        self._failures: Dict[str, int] = {}
        # State: tool_name -> timestamp when it was tripped
        self._tripped_at: Dict[str, float] = {}
        
        self._lock = threading.Lock()

    def is_open(self, tool_name: str) -> bool:
        """
        Returns True if the circuit is 'open' (blocked).
        """
        with self._lock:
            if tool_name not in self._tripped_at:
                return False
            
            tripped_time = self._tripped_at[tool_name]
            if (time.time() - tripped_time) > self.recovery_timeout:
                # Half-open logic: allow a trial
                logger.info("circuit_breaker_half_open", tool=tool_name)
                del self._tripped_at[tool_name]
                # Reset failures so we don't immediately trip again
                self._failures[tool_name] = self.failure_threshold - 1
                return False
            
            return True

    def record_failure(self, tool_name: str):
        """
        Increments failure count and trips circuit if threshold reached.
        """
        with self._lock:
            self._failures[tool_name] = self._failures.get(tool_name, 0) + 1
            if self._failures[tool_name] >= self.failure_threshold:
                if tool_name not in self._tripped_at:
                    logger.error("circuit_breaker_tripped", tool=tool_name, failures=self._failures[tool_name])
                self._tripped_at[tool_name] = time.time()

    def record_success(self, tool_name: str):
        """
        Resets failure count if a call succeeds.
        """
        with self._lock:
            if tool_name in self._failures:
                self._failures[tool_name] = 0
            if tool_name in self._tripped_at:
                logger.info("circuit_breaker_closed", tool=tool_name)
                del self._tripped_at[tool_name]

# Global singleton for the process
tool_circuit_breaker = CircuitBreaker()
