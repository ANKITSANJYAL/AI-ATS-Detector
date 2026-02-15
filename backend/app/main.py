"""
FastAPI application entry point.
Self-documenting API with OpenAPI integration.

NOTE: uvloop 0.21 + Python 3.13 causes a deadlock where the server
accepts TCP connections but never processes HTTP requests.
Always start with: uvicorn app.main:app --loop asyncio
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.models import Base
from app.db.session import close_db, get_engine
from app.middleware.api_version import APIVersionMiddleware
from app.middleware.usage_tracker import UsageTrackerMiddleware
from app.services.mcp_client import close_mcp_client
from app.services.redis_client import close_redis_client, get_redis_client

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Initialize Sentry (no-op if DSN is empty)
_settings_init = get_settings()
if _settings_init.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=_settings_init.sentry_dsn,
            environment=_settings_init.environment,
            release=f"docguard@{_settings_init.app_version}",
            traces_sample_rate=0.2 if _settings_init.environment == "production" else 1.0,
            profiles_sample_rate=0.1,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            send_default_pii=False,
        )
        logger.info("Sentry error tracking initialized")
    except ImportError:
        logger.warning("sentry-sdk not installed — error tracking disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting DocGuard & CareerMatch API")

    # Initialize Redis connection
    await get_redis_client()
    logger.info("Redis connected")

    # Verify database connectivity (migrations managed by Alembic)
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(Base.metadata.tables["documents"].select().limit(0))
        logger.info("Database connection verified (migrations managed by Alembic)")
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        logger.warning("Application starting in DEGRADED mode — DB endpoints will fail")

    # Pre-warm ML models to avoid cold-start latency on first request
    try:
        from app.services.ai_classifier import get_ai_classifier
        classifier = get_ai_classifier()
        classifier._ensure_models()
        logger.info("AI detection models pre-warmed")
    except Exception as exc:
        logger.warning(f"Model pre-warming failed (will lazy-load): {exc}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_redis_client()
    await close_mcp_client()
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI application
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
# DocGuard & CareerMatch AI SaaS

Professional AI-powered document analysis platform.

## Features

### 🛡️ AI Document Guard
Forensic linguistic analysis to detect AI-generated content.
- Multi-dimensional feature extraction
- High-accuracy detection algorithms
- Detailed analysis reports

### 🎯 Strategic Career Match
ATS compatibility scoring and gap analysis.
- Semantic similarity matching
- Keyword optimization analysis
- Actionable improvement recommendations

## Authentication
All endpoints require Bearer token authentication using Clerk.

## Rate Limiting
60 requests per minute per user.

## Billing
Metered billing via Stripe. Usage is tracked automatically.
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "documents",
            "description": "Document management and analysis operations",
        },
        {
            "name": "jobs",
            "description": "Job description management",
        },
        {
            "name": "webhooks",
            "description": "Webhook endpoints for external integrations",
        },
        {
            "name": "health",
            "description": "Health check and system status",
        },
    ],
    lifespan=lifespan,
)

# Configure CORS — explicit methods and headers, not wildcards
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Add usage tracking middleware
app.add_middleware(UsageTrackerMiddleware)

# Add API versioning headers middleware
app.add_middleware(APIVersionMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get(
    "/",
    tags=["health"],
    summary="Root endpoint",
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "status": "operational",
    }


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Check the health status of all system components",
)
async def health_check():
    """
    Health check endpoint.
    Returns health status of all services with real connectivity checks.
    """
    from datetime import UTC, datetime

    from app.agents.orchestrator import get_orchestrator_agent

    orchestrator = get_orchestrator_agent()

    # Real health checks (database, Redis, ML models, agents)
    agent_health = await orchestrator.health_check()

    all_healthy = all(agent_health.values())
    # Degraded if any non-critical service is down, unhealthy if critical ones are
    critical = ["database", "detector_agent"]
    critical_healthy = all(agent_health.get(k, False) for k in critical)

    if all_healthy:
        health_status = "healthy"
    elif critical_healthy:
        health_status = "degraded"
    else:
        health_status = "unhealthy"

    return {
        "status": health_status,
        "version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
        "services": agent_health,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        loop="asyncio",
    )
