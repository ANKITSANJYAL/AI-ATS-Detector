"""
conftest.py — Shared test fixtures.
Provides FastAPI TestClient for integration testing.

Note: Uses session-scoped event loop to avoid cross-test loop
contamination from starlette BaseHTTPMiddleware and persistent
Redis/DB connections.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

pytest_plugins = ("pytest_asyncio",)


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


@pytest_asyncio.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP client bound to the FastAPI app.
    Uses ASGI transport so no actual server is needed.
    Session-scoped to share the event loop with singleton services.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
