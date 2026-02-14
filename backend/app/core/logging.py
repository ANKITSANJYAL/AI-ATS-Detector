"""
Structured logging configuration for the application.
Follows Google Cloud Logging structured format.
"""
import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that adds application context.
    Compatible with Google Cloud Logging and other structured log aggregators.
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
