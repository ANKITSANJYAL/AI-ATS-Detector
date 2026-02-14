"""
Usage tracking middleware for metered billing.
Records API usage to PostgreSQL, reports to Stripe, and adds rate-limit headers.

Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid event-loop
deadlocks with uvloop when multiple middlewares are stacked.
"""
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger, set_request_id
from app.db.session import get_session_factory
from app.db.models import UsageRecord

logger = get_logger(__name__)

BILLABLE_PATHS = [
    "/api/v1/documents/detect",
    "/api/v1/documents/score",
]


class UsageTrackerMiddleware:
    """
    Pure-ASGI middleware to track API usage for billing purposes.
    Persists usage records to PostgreSQL and reports to Stripe.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http",):
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        # Inject request ID for distributed tracing
        headers = dict(scope.get("headers", []))
        incoming_id = headers.get(b"x-request-id", b"").decode() or None
        request_id = set_request_id(incoming_id)

        status_code = 200

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                raw_headers = list(message.get("headers", []))
                duration = time.time() - start_time
                raw_headers.append((b"x-request-id", request_id.encode()))
                raw_headers.append((b"x-process-time", f"{duration:.3f}".encode()))
                message = {**message, "headers": raw_headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration = time.time() - start_time
        path = scope.get("path", "")

        if self._is_billable_endpoint(path):
            try:
                await self._track_usage(scope, path, status_code, duration)
            except Exception as exc:
                logger.warning(f"Usage tracking failed: {exc}")

    async def _track_usage(
        self, scope: Scope, path: str, status_code: int, duration: float
    ) -> None:
        """Persist usage record and report to Stripe."""
        state = scope.get("state", {})
        user_id = state.get("user_id") if isinstance(state, dict) else None
        if not user_id:
            return

        feature = self._get_feature_from_path(path)
        duration_ms = int(duration * 1000)

        try:
            factory = get_session_factory()
            async with factory() as session:
                record = UsageRecord(
                    user_id=user_id,
                    feature=feature,
                    endpoint=path,
                    status_code=str(status_code),
                    duration_ms=duration_ms,
                )
                session.add(record)
                await session.commit()
        except Exception as exc:
            logger.warning(f"Failed to persist usage record: {exc}")

        if status_code < 400:
            try:
                from app.services.billing import get_billing_service
                billing = get_billing_service()
                await billing.report_usage(user_id, feature, quantity=1)
            except Exception as exc:
                logger.debug(f"Stripe usage report skipped: {exc}")

        logger.info(
            "Billable usage",
            extra={
                "user_id": user_id,
                "feature": feature,
                "endpoint": path,
                "method": scope.get("method", ""),
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

    @staticmethod
    def _is_billable_endpoint(path: str) -> bool:
        return any(path.startswith(bp) for bp in BILLABLE_PATHS)

    @staticmethod
    def _get_feature_from_path(path: str) -> str:
        if "/detect" in path:
            return "ai_detection"
        elif "/score" in path:
            return "ats_scoring"
        return "unknown"
