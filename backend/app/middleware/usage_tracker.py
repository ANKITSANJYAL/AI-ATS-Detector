"""
Usage tracking middleware for metered billing.
Records API usage to PostgreSQL, reports to Stripe, and adds rate-limit headers.
"""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger, set_request_id
from app.db.session import get_session_factory
from app.db.models import UsageRecord

logger = get_logger(__name__)


class UsageTrackerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API usage for billing purposes.
    Persists usage records to PostgreSQL and reports to Stripe.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        start_time = time.time()

        # Inject request ID for distributed tracing
        incoming_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(incoming_id)

        response = await call_next(request)

        # Echo request ID back in response
        response.headers["X-Request-ID"] = request_id

        duration = time.time() - start_time

        if self._is_billable_endpoint(request.url.path):
            user_id = getattr(request.state, "user_id", None)

            if user_id:
                feature = self._get_feature_from_path(request.url.path)
                duration_ms = int(duration * 1000)

                # Persist to DB (non-blocking: errors here must not fail the request)
                try:
                    factory = get_session_factory()
                    async with factory() as session:
                        record = UsageRecord(
                            user_id=user_id,
                            feature=feature,
                            endpoint=request.url.path,
                            status_code=str(response.status_code),
                            duration_ms=duration_ms,
                        )
                        session.add(record)
                        await session.commit()
                except Exception as exc:
                    logger.warning(f"Failed to persist usage record: {exc}")

                # Report to Stripe (fire-and-forget, non-blocking)
                if response.status_code < 400:
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
                        "endpoint": request.url.path,
                        "method": request.method,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )

        # Add processing time header
        response.headers["X-Process-Time"] = f"{duration:.3f}"
        return response

    def _is_billable_endpoint(self, path: str) -> bool:
        billable_paths = [
            "/api/v1/documents/detect",
            "/api/v1/documents/score",
        ]
        return any(path.startswith(bp) for bp in billable_paths)

    def _get_feature_from_path(self, path: str) -> str:
        if "/detect" in path:
            return "ai_detection"
        elif "/score" in path:
            return "ats_scoring"
        return "unknown"
