"""
Stripe billing service.
Handles customer creation, checkout sessions, usage reporting,
and Customer Portal integration.
"""
import json
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BillingService:
    """
    Stripe integration service for metered SaaS billing.

    Responsibilities:
    - Create/retrieve Stripe customers linked to Clerk user IDs
    - Generate checkout sessions for subscription plans
    - Report metered usage for billing
    - Create Customer Portal sessions for self-service management
    """

    def __init__(self):
        self._stripe = None

    def _ensure_stripe(self):
        """Lazy-load stripe SDK."""
        if self._stripe is not None:
            return
        try:
            import stripe
            settings = get_settings()
            stripe.api_key = settings.stripe_api_key
            self._stripe = stripe
            logger.info("Stripe SDK initialized")
        except ImportError:
            logger.error("stripe package not installed")
            raise RuntimeError("Stripe is not available")

    async def get_or_create_customer(
        self, user_id: str, email: str | None = None
    ) -> str:
        """
        Get existing Stripe customer or create one.

        Args:
            user_id: Clerk user ID
            email: User email address

        Returns:
            Stripe customer ID
        """
        self._ensure_stripe()
        from app.services.redis_client import get_redis_client

        redis = await get_redis_client()

        # Check cache
        cache_key = f"stripe:customer:{user_id}"
        cached = await redis.get(cache_key)
        if cached:
            return cached

        # Search Stripe for existing customer
        customers = self._stripe.Customer.search(
            query=f"metadata['clerk_user_id']:'{user_id}'"
        )

        if customers.data:
            customer_id = customers.data[0].id
        else:
            # Create new customer
            customer = self._stripe.Customer.create(
                email=email,
                metadata={"clerk_user_id": user_id},
                description=f"DocGuard user {user_id}",
            )
            customer_id = customer.id
            logger.info(f"Created Stripe customer {customer_id} for user {user_id}")

        # Cache for 24 hours
        await redis.set(cache_key, customer_id, ttl=86400)
        return customer_id

    async def create_checkout_session(
        self,
        user_id: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """
        Create a Stripe Checkout session for subscription.

        Args:
            user_id: Clerk user ID
            plan: Plan identifier ("pro" or "enterprise")
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel

        Returns:
            Checkout session URL
        """
        self._ensure_stripe()
        settings = get_settings()

        customer_id = await self.get_or_create_customer(user_id)

        price_map = {
            "ai_detection": settings.stripe_price_id_ai_detection,
            "ats_scoring": settings.stripe_price_id_ats_scoring,
        }

        line_items = []
        for feature, price_id in price_map.items():
            if price_id:
                line_items.append({"price": price_id})

        if not line_items:
            raise ValueError("No Stripe price IDs configured")

        session = self._stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"clerk_user_id": user_id, "plan": plan},
        )

        return session.url

    async def create_portal_session(self, user_id: str, return_url: str) -> str:
        """
        Create a Stripe Customer Portal session for subscription management.

        Args:
            user_id: Clerk user ID
            return_url: URL to return to after portal

        Returns:
            Portal session URL
        """
        self._ensure_stripe()

        customer_id = await self.get_or_create_customer(user_id)

        session = self._stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        return session.url

    async def report_usage(self, user_id: str, feature: str, quantity: int = 1) -> bool:
        """
        Report metered usage to Stripe.

        Args:
            user_id: Clerk user ID
            feature: Feature used ("ai_detection" or "ats_scoring")
            quantity: Number of units consumed

        Returns:
            True if usage was reported successfully
        """
        self._ensure_stripe()
        settings = get_settings()

        price_map = {
            "ai_detection": settings.stripe_price_id_ai_detection,
            "ats_scoring": settings.stripe_price_id_ats_scoring,
        }

        price_id = price_map.get(feature)
        if not price_id:
            logger.warning(f"No Stripe price ID for feature: {feature}")
            return False

        try:
            customer_id = await self.get_or_create_customer(user_id)

            # Find active subscription for this customer
            subscriptions = self._stripe.Subscription.list(
                customer=customer_id, status="active", limit=1
            )

            if not subscriptions.data:
                logger.warning(f"No active subscription for user {user_id}")
                return False

            subscription = subscriptions.data[0]

            # Find the subscription item for this price
            sub_item = None
            for item in subscription["items"]["data"]:
                if item["price"]["id"] == price_id:
                    sub_item = item
                    break

            if not sub_item:
                logger.warning(f"No subscription item for price {price_id}")
                return False

            # Report usage
            self._stripe.SubscriptionItem.create_usage_record(
                sub_item["id"],
                quantity=quantity,
                timestamp=int(datetime.now(UTC).timestamp()),
                action="increment",
            )

            logger.info(
                f"Reported {quantity} usage for {feature} (user={user_id})"
            )
            return True

        except Exception as exc:
            logger.error(f"Failed to report Stripe usage: {exc}")
            return False

    async def get_subscription_status(self, user_id: str) -> dict:
        """
        Get current subscription status for a user.

        Returns:
            Dict with status, plan, current_period_end, etc.
        """
        self._ensure_stripe()

        try:
            customer_id = await self.get_or_create_customer(user_id)

            subscriptions = self._stripe.Subscription.list(
                customer=customer_id, limit=1
            )

            if not subscriptions.data:
                return {
                    "status": "free",
                    "plan": "free",
                    "usage_limit": 5,
                    "current_period_end": None,
                }

            sub = subscriptions.data[0]
            return {
                "status": sub["status"],
                "plan": sub.get("metadata", {}).get("plan", "pro"),
                "usage_limit": -1,  # Unlimited for paid plans
                "current_period_end": datetime.fromtimestamp(
                    sub["current_period_end"], tz=UTC
                ).isoformat(),
                "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            }

        except Exception as exc:
            logger.error(f"Failed to get subscription status: {exc}")
            return {
                "status": "unknown",
                "plan": "free",
                "usage_limit": 5,
                "current_period_end": None,
            }


# Singleton
_billing_service: BillingService | None = None


def get_billing_service() -> BillingService:
    """Get or create the billing service singleton."""
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService()
    return _billing_service
