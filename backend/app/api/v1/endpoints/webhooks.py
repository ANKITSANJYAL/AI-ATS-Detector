"""
Webhook endpoints.
Handles webhooks from external services (Stripe, etc).
"""
import hashlib
import hmac
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.redis_client import RedisClient, get_redis_client

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/stripe",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook handler",
    description="""
    Receive and process Stripe webhook events for billing.
    Handles payment events, subscription changes, and usage reporting.

    **Requires** a valid Stripe-Signature header.
    """,
)
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
    redis: Annotated[RedisClient, Depends(get_redis_client)] = None,
) -> dict:
    """
    Handle Stripe webhook events.
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature",
        )

    if not settings.stripe_webhook_secret:
        logger.error("Stripe webhook secret not configured — rejecting webhook")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook processing not configured",
        )

    # Get raw body
    body = await request.body()

    # Verify webhook signature — MUST pass in all environments
    if not _verify_stripe_signature(
        body,
        stripe_signature,
        settings.stripe_webhook_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse webhook data
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from None

    event_type = event_data.get("type")
    event_id = event_data.get("id", "unknown")

    # Idempotency: skip already-processed events
    idempotency_key = f"stripe:event:{event_id}"
    if await redis.get(idempotency_key):
        logger.info(f"Duplicate Stripe webhook skipped: {event_id}")
        return {"received": True, "duplicate": True}

    logger.info(f"Processing Stripe webhook: {event_type} (id={event_id})")

    # Handle different event types
    if event_type == "invoice.payment_succeeded":
        await _handle_payment_succeeded(event_data, redis)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(event_data, redis)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(event_data, redis)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(event_data, redis)
    else:
        logger.info(f"Unhandled webhook event type: {event_type}")

    # Mark event as processed (7-day TTL for idempotency)
    await redis.set(idempotency_key, "1", ttl=86400 * 7)

    return {"received": True}


def _verify_stripe_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify Stripe webhook signature.

    Args:
        payload: Raw webhook payload
        signature: Stripe-Signature header value
        secret: Webhook signing secret

    Returns:
        True if signature is valid
    """
    if not secret:
        logger.error("Stripe webhook secret is empty — verification cannot proceed")
        return False

    try:
        # Extract timestamp and signature from header
        parts = dict(part.split("=", 1) for part in signature.split(","))
        timestamp = parts.get("t")
        sig = parts.get("v1")

        if not timestamp or not sig:
            return False

        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode()}"
        expected_sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, sig)

    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False


async def _handle_payment_succeeded(event_data: dict, redis: RedisClient) -> None:
    """Handle successful payment event."""
    invoice = event_data.get("data", {}).get("object", {})
    customer_id = invoice.get("customer")
    amount = invoice.get("amount_paid", 0)

    logger.info(f"Payment succeeded for customer {customer_id}: ${amount / 100:.2f}")

    # Persist payment record
    record = json.dumps({
        "customer_id": customer_id,
        "amount": amount,
        "event_id": event_data.get("id"),
        "status": "succeeded",
    })
    await redis.set(
        f"payment:{customer_id}:{event_data.get('id')}",
        record,
        ttl=86400 * 90,  # 90 days
    )


async def _handle_payment_failed(event_data: dict, redis: RedisClient) -> None:
    """Handle failed payment event."""
    invoice = event_data.get("data", {}).get("object", {})
    customer_id = invoice.get("customer")

    logger.warning(f"Payment failed for customer {customer_id}")

    record = json.dumps({
        "customer_id": customer_id,
        "event_id": event_data.get("id"),
        "status": "failed",
    })
    await redis.set(
        f"payment_failure:{customer_id}:{event_data.get('id')}",
        record,
        ttl=86400 * 90,
    )


async def _handle_subscription_updated(event_data: dict, redis: RedisClient) -> None:
    """Handle subscription update event."""
    subscription = event_data.get("data", {}).get("object", {})
    customer_id = subscription.get("customer")
    status_value = subscription.get("status")

    logger.info(f"Subscription updated for customer {customer_id}: {status_value}")

    await redis.set(
        f"subscription:{customer_id}",
        json.dumps({"status": status_value, "event_id": event_data.get("id")}),
        ttl=86400 * 365,
    )


async def _handle_subscription_deleted(event_data: dict, redis: RedisClient) -> None:
    """Handle subscription cancellation event."""
    subscription = event_data.get("data", {}).get("object", {})
    customer_id = subscription.get("customer")

    logger.info(f"Subscription cancelled for customer {customer_id}")

    await redis.set(
        f"subscription:{customer_id}",
        json.dumps({"status": "cancelled", "event_id": event_data.get("id")}),
        ttl=86400 * 365,
    )
