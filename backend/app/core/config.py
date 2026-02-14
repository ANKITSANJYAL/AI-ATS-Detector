"""
Core configuration module using Pydantic Settings.
All environment variables are type-safe and validated.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    Follows 12-factor app principles for configuration management.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(
        default="DocGuard & CareerMatch",
        description="Application name for logging and monitoring",
    )
    app_version: str = Field(default="1.0.0", description="API version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 route prefix")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # Database
    postgres_dsn: PostgresDsn = Field(
        default="postgresql://user:pass@localhost:5432/docguard",
        description="PostgreSQL connection string",
    )

    # Redis
    redis_dsn: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for caching and job queue",
    )
    redis_ttl: int = Field(default=3600, description="Default cache TTL in seconds")

    # Background Jobs (reserved for future async processing)
    # celery_broker_url and celery_result_backend are available
    # but not actively used — processing is synchronous for now.
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL (reserved for future use)",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL (reserved for future use)",
    )

    # LLM Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for LLM operations",
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        description="OpenAI model to use",
    )
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude models",
    )

    # MCP Server
    mcp_server_url: str = Field(
        default="http://localhost:3001",
        description="Model Context Protocol server URL",
    )

    # Stripe Billing
    stripe_api_key: str = Field(
        default="",
        description="Stripe secret API key for metered billing",
    )
    stripe_webhook_secret: str = Field(
        default="",
        description="Stripe webhook signing secret",
    )
    stripe_price_id_ai_detection: str = Field(
        default="",
        description="Stripe price ID for AI detection feature",
    )
    stripe_price_id_ats_scoring: str = Field(
        default="",
        description="Stripe price ID for ATS scoring feature",
    )

    # Clerk Authentication
    clerk_secret_key: str = Field(
        default="",
        description="Clerk secret key for JWT verification",
    )
    clerk_publishable_key: str = Field(
        default="",
        description="Clerk publishable key (frontend)",
    )
    clerk_domain: str = Field(
        default="",
        description="Clerk domain for JWKS endpoint (e.g. 'your-app.clerk.accounts.dev')",
    )

    # Document Processing
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum upload file size in megabytes",
    )
    allowed_file_types: list[str] = Field(
        default=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "text/plain",
            "image/jpeg",
            "image/png",
            "application/octet-stream",
        ],
        description="Allowed MIME types for document uploads",
    )

    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=60,
        description="API rate limit per minute per user",
    )

    # Observability
    sentry_dsn: str = Field(
        default="",
        description="Sentry DSN for error tracking (leave empty to disable)",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    @field_validator("max_file_size_mb")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Ensure file size is reasonable."""
        if v < 1 or v > 100:
            raise ValueError("max_file_size_mb must be between 1 and 100")
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """
        Reject wildcard CORS in production.
        Ensures only explicit origins are allowed.
        """
        for origin in v:
            if origin == "*":
                import os
                env = os.getenv("ENVIRONMENT", "development")
                if env == "production":
                    raise ValueError(
                        "Wildcard '*' CORS origin is not allowed in production. "
                        "Specify explicit domains."
                    )
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to ensure single instance across application.
    """
    return Settings()
