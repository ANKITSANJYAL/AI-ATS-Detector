"""
API versioning middleware.
Adds version headers and deprecation notices to API responses.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Adds standard API versioning headers to every response:
    - X-API-Version: current API version
    - X-API-Deprecation: deprecation notice for sunset endpoints (if any)
    """

    # Map of deprecated path prefixes → sunset date (ISO 8601)
    # Add entries here when deprecating endpoints.
    DEPRECATED_PATHS: dict[str, str] = {
        # Example: "/api/v0": "2025-06-01",
    }

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        settings = get_settings()
        response.headers["X-API-Version"] = settings.app_version

        # Check if the requested path hits a deprecated prefix
        path = request.url.path
        for prefix, sunset_date in self.DEPRECATED_PATHS.items():
            if path.startswith(prefix):
                response.headers["Deprecation"] = "true"
                response.headers["Sunset"] = sunset_date
                response.headers["Link"] = (
                    f'<{settings.api_v1_prefix}>; rel="successor-version"'
                )
                break

        return response
