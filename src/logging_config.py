from __future__ import annotations

import logging
import sys
from typing import Any, Mapping

import structlog

from .config import get_settings


def _add_app_context(
    logger: structlog.BoundLogger,
    method_name: str,
    event_dict: Mapping[str, Any],
) -> Mapping[str, Any]:
    """
    Enrich log records with basic app context (name, env).
    """
    settings = get_settings()
    event_dict["app"] = settings.app_name
    event_dict["env"] = settings.env
    return event_dict


def setup_logging() -> None:
    """
    Configure structlog + stdlib logging for JSON logs.

    Call this once at startup (e.g., in init_resources).
    """
    settings = get_settings()

    # Configure root logging for libraries
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    # Reduce noise if needed
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    processors = [
        structlog.contextvars.merge_contextvars,  # include bound contextvars
        _add_app_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )
