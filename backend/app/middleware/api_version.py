"""
API versioning middleware.
Adds version headers and deprecation notices to API responses.

Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid event-loop
deadlocks with uvloop when multiple middlewares are stacked.
"""
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings


class APIVersionMiddleware:
    """
    Adds standard API versioning headers to every response:
    - X-API-Version: current API version
    - X-API-Deprecation: deprecation notice for sunset endpoints (if any)
    """

    # Map of deprecated path prefixes → sunset date (ISO 8601)
    DEPRECATED_PATHS: dict[str, str] = {
        # Example: "/api/v0": "2025-06-01",
    }

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http",):
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        path = scope.get("path", "")

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers", []))
                raw_headers.append(
                    (b"x-api-version", settings.app_version.encode())
                )

                for prefix, sunset_date in self.DEPRECATED_PATHS.items():
                    if path.startswith(prefix):
                        raw_headers.append((b"deprecation", b"true"))
                        raw_headers.append((b"sunset", sunset_date.encode()))
                        raw_headers.append((
                            b"link",
                            f'<{settings.api_v1_prefix}>; rel="successor-version"'.encode(),
                        ))
                        break

                message = {**message, "headers": raw_headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
