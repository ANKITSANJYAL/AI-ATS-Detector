"""
Billing API endpoints.
Handles subscription management, checkout, and usage queries.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user_id
from app.core.logging import get_logger
from app.services.billing import BillingService, get_billing_service

logger = get_logger(__name__)

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────

class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    plan: str = Field(
        default="pro",
        description="Subscription plan (pro or enterprise)",
    )
    success_url: str = Field(
        default="http://localhost:3000/dashboard?checkout=success",
        description="Redirect URL after successful checkout",
    )
    cancel_url: str = Field(
        default="http://localhost:3000/pricing?checkout=cancelled",
        description="Redirect URL if checkout is cancelled",
    )


class CheckoutResponse(BaseModel):
    """Checkout session created."""
    checkout_url: str = Field(description="Stripe Checkout URL to redirect user to")


class PortalRequest(BaseModel):
    """Request for customer portal session."""
    return_url: str = Field(
        default="http://localhost:3000/dashboard",
        description="URL to return to after portal",
    )


class PortalResponse(BaseModel):
    """Customer portal session created."""
    portal_url: str = Field(description="Stripe Customer Portal URL")


class SubscriptionStatusResponse(BaseModel):
    """Current subscription status."""
    status: str = Field(description="Subscription status (free, active, past_due, etc.)")
    plan: str = Field(description="Current plan name")
    usage_limit: int = Field(description="Remaining usage (-1 for unlimited)")
    current_period_end: str | None = Field(description="Current billing period end date")
    cancel_at_period_end: bool = Field(default=False, description="Whether subscription cancels at period end")


class UsageSummaryResponse(BaseModel):
    """Usage summary for the current billing period."""
    ai_detection_count: int = Field(description="Number of AI detections this period")
    ats_scoring_count: int = Field(description="Number of ATS scores this period")
    total_usage: int = Field(description="Total billable events")


# ── Endpoints ─────────────────────────────────────────────────

@router.get(
    "/status",
    response_model=SubscriptionStatusResponse,
    summary="Get subscription status",
    description="Returns the current user's subscription status and plan details.",
)
async def get_subscription_status(
    user_id: Annotated[str, Depends(get_current_user_id)],
    billing: Annotated[BillingService, Depends(get_billing_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SubscriptionStatusResponse:
    """Get current subscription status."""
    if not settings.stripe_api_key:
        return SubscriptionStatusResponse(
            status="free",
            plan="free",
            usage_limit=5,
            current_period_end=None,
            cancel_at_period_end=False,
        )

    result = await billing.get_subscription_status(user_id)
    return SubscriptionStatusResponse(**result)


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create checkout session",
    description="Creates a Stripe Checkout session for subscribing to a plan.",
)
async def create_checkout(
    request: CheckoutRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    billing: Annotated[BillingService, Depends(get_billing_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CheckoutResponse:
    """Create a Stripe Checkout session."""
    if not settings.stripe_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )

    try:
        url = await billing.create_checkout_session(
            user_id=user_id,
            plan=request.plan,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutResponse(checkout_url=url)
    except Exception as exc:
        logger.error(f"Checkout session failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post(
    "/portal",
    response_model=PortalResponse,
    summary="Open customer portal",
    description="Creates a Stripe Customer Portal session for managing subscriptions.",
)
async def create_portal_session(
    request: PortalRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    billing: Annotated[BillingService, Depends(get_billing_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PortalResponse:
    """Create a Stripe Customer Portal session."""
    if not settings.stripe_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )

    try:
        url = await billing.create_portal_session(
            user_id=user_id,
            return_url=request.return_url,
        )
        return PortalResponse(portal_url=url)
    except Exception as exc:
        logger.error(f"Portal session failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session",
        )


@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
    summary="Get usage summary",
    description="Returns usage counts for the current billing period.",
)
async def get_usage_summary(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UsageSummaryResponse:
    """Get usage summary from database."""
    from sqlalchemy import func, select
    from app.db.session import get_session_factory
    from app.db.models import UsageRecord

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(
                UsageRecord.feature,
                func.count().label("count"),
            )
            .where(UsageRecord.user_id == user_id)
            .group_by(UsageRecord.feature)
        )
        result = await session.execute(stmt)
        rows = result.all()

    counts = {row.feature: row.count for row in rows}
    ai_count = counts.get("ai_detection", 0)
    ats_count = counts.get("ats_scoring", 0)

    return UsageSummaryResponse(
        ai_detection_count=ai_count,
        ats_scoring_count=ats_count,
        total_usage=ai_count + ats_count,
    )
