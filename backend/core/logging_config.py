from __future__ import annotations

import logging.config
import sys
from typing import Any


LOGGING_CONFIG_BASE: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(lineno)d",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s%(asctime)s [%(levelname)s] %(cyan)s%(name)s%(reset)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "json",
            "stream": sys.stdout,
        },
        "console_verbose": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "verbose",
            "stream": sys.stdout,
        },
        "console_colored": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "colored",
            "stream": sys.stdout,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "verbose",
            "filename": "logs/app.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "logs/error.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf8",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console_colored"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console_colored"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console_colored"],
            "level": "INFO",
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "handlers": ["console_verbose"],
            "level": "WARNING",
            "propagate": False,
        },
        "aiosmtplib": {
            "handlers": ["console_verbose"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console_colored", "file", "error_file"],
        "level": "INFO",
    },
}

LOGGING_CONFIG_PRODUCTION: dict[str, Any] = {
    **LOGGING_CONFIG_BASE,
    "root": {
        "handlers": ["console_json", "file", "error_file"],
        "level": "INFO",
    },
}

LOGGING_CONFIG_DEVELOPMENT: dict[str, Any] = {
    **LOGGING_CONFIG_BASE,
    "root": {
        "handlers": ["console_colored", "file", "error_file"],
        "level": "DEBUG",
    },
}


def setup_logging(environment: str | None = None) -> None:
    if environment is None:
        from core.config import get_settings

        settings = get_settings()
        environment = settings.ENVIRONMENT

    if environment.lower() == "production":
        config = LOGGING_CONFIG_PRODUCTION
    else:
        config = LOGGING_CONFIG_DEVELOPMENT

    logging.config.dictConfig(config)
