"""
Structured logging configuration for the application.
Follows Google Cloud Logging structured format.

Production logging pipeline:
  Application → JSON stdout → Docker log driver → aggregator
  Supported aggregators: Google Cloud Logging, ELK, Datadog, Grafana Loki

  All logs include: app, version, environment, severity, logger, request_id (when available).
  Set LOG_LEVEL in .env to control verbosity.
"""
import contextvars
import logging
import sys
from typing import Any
from uuid import uuid4

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

# Context variable for request ID tracing across async calls
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)


def set_request_id(request_id: str | None = None) -> str:
    """Set (or generate) a request ID for the current async context."""
    rid = request_id or uuid4().hex[:16]
    request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """Get the current request ID."""
    return request_id_var.get("")


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that adds application context.
    Compatible with Google Cloud Logging, ELK, Datadog, and
    other structured log aggregators.

    Emitted fields:
      timestamp, severity, logger, app, version, environment, request_id, message
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        settings = get_settings()
        log_record["severity"] = record.levelname
        log_record["logger"] = record.name
        log_record["app"] = settings.app_name
        log_record["version"] = settings.app_version
        log_record["environment"] = settings.environment

        # Attach request ID if available
        rid = get_request_id()
        if rid:
            log_record["request_id"] = rid


def setup_logging() -> None:
    """
    Configure application-wide logging.
    Uses structured JSON logging for production environments.
    """
    settings = get_settings()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Use JSON formatter for production, simple format for development
    if settings.environment == "production":
        formatter = CustomJsonFormatter(
            "%(asctime)s %(severity)s %(logger)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
