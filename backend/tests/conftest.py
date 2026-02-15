"""
conftest.py — Shared test fixtures.
Provides FastAPI TestClient for integration testing.

Note: Uses session-scoped event loop to avoid cross-test loop
contamination from starlette BaseHTTPMiddleware and persistent
Redis/DB connections.
"""
import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

pytest_plugins = ("pytest_asyncio",)


# ── Marker: skip tests that require an OpenAI API key ──────────
requires_openai = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping test that requires OpenAI",
)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a single event loop shared across ALL tests in the session.
    Required because FastAPI app singletons (Redis pool, DB engine) bind
    to the loop they're first called on.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_db_tables():
    """
    Auto-create all ORM tables before the test session starts.
    This ensures the CI Postgres service has the schema even when
    Alembic migrations haven't been applied.
    """
    try:
        from app.db.models import Base
        from app.db.session import get_engine

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        # If DB is unavailable (e.g. local dev without Postgres),
        # tests that don't need DB will still run fine.
        pass
    yield


@pytest_asyncio.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient]:
    """
    Provide an async HTTP client bound to the FastAPI app.
    Uses ASGI transport so no actual server is needed.
    Session-scoped to share the event loop with singleton services.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
