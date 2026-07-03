from __future__ import annotations

import logging
import sys
import uuid
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger

from core.config import get_settings

settings = get_settings()


def add_correlation_id(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    correlation_id = event_dict.get("correlation_id")
    if correlation_id is None:
        correlation_id = uuid.uuid4().hex[:16]
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_app_info(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    event_dict["app"] = settings.PROJECT_NAME
    event_dict["version"] = settings.VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def drop_color_message(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    if "message" in event_dict and isinstance(event_dict["message"], str):
        event_dict["message"] = event_dict["message"].replace("\x1b[", "")
        event_dict["message"] = event_dict["message"].replace("m", "")
    return event_dict


def setup_structlog() -> None:
    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        add_correlation_id,
        add_app_info,
    ]

    if settings.LOG_JSON or settings.ENVIRONMENT.lower() == "production":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(
                colors=True,
                sort_keys=False,
            ),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "httpx"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name or __name__)
