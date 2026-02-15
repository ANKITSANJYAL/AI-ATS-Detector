"""
Dependency injection for FastAPI routes.
Provides reusable dependencies for authentication, rate limiting, and services.
"""
import json
from typing import Annotated

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.redis_client import RedisClient, get_redis_client

logger = get_logger(__name__)

# Cached JWKS keys — refreshed hourly via TTL in Redis
_JWKS_CACHE_KEY = "clerk:jwks"


async def _fetch_clerk_jwks(settings: Settings, redis: RedisClient) -> dict:
    """
    Fetch and cache Clerk's JWKS (JSON Web Key Set).

    Args:
        settings: Application settings
        redis: Redis client for caching

    Returns:
        JWKS dictionary

    Raises:
        HTTPException: If JWKS cannot be fetched
    """
    # Try cache first
    cached = await redis.get(_JWKS_CACHE_KEY)
    if cached:
        return json.loads(cached)

    # Fetch from Clerk
    clerk_domain = settings.clerk_domain
    if not clerk_domain:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk domain not configured",
        )

    jwks_url = f"https://{clerk_domain}/.well-known/jwks.json"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks_data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch Clerk JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from e

    # Cache for 1 hour
    await redis.set(_JWKS_CACHE_KEY, json.dumps(jwks_data), ttl=3600)
    return jwks_data


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
    redis: Annotated[RedisClient, Depends(get_redis_client)] = None,
) -> str:
    """
    Extract and validate user ID from Clerk JWT token.
    In development mode with DEBUG=true, returns a default test user ID.

    Args:
        authorization: Bearer token from Authorization header
        settings: Application settings
        redis: Redis client

    Returns:
        User ID from validated JWT token or test user in development

    Raises:
        HTTPException: If token is missing or invalid
    """
    # Development bypass — only in explicit debug mode
    if settings.debug and settings.environment == "development":
        return "dev-user-id"

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise ValueError("Invalid authorization header format")
        token = parts[1]

        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise ValueError("Token missing key ID (kid)")

        # Fetch JWKS and find matching key
        jwks_data = await _fetch_clerk_jwks(settings, redis)
        signing_key = None
        for key in jwks_data.get("keys", []):
            if key.get("kid") == kid:
                signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if signing_key is None:
            raise ValueError("No matching signing key found")

        # Verify and decode the JWT with full signature verification
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
            },
        )

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token missing user ID (sub claim)")

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def verify_rate_limit(
    user_id: Annotated[str, Depends(get_current_user_id)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> None:
    """
    Verify user hasn't exceeded rate limit.
    Uses atomic Redis pipeline to prevent race conditions.
    Gracefully degrades: if Redis is down, rate limiting is skipped
    (better to serve requests than to reject everyone).

    Args:
        user_id: Authenticated user ID
        redis: Redis client for rate limiting
        settings: Application settings

    Raises:
        HTTPException: If rate limit exceeded
    """
    try:
        key = f"rate_limit:{user_id}"

        # Atomic: increment and set expiry in a single pipeline
        pipe = redis.client.pipeline(transaction=True)
        pipe.incr(key)
        pipe.ttl(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        count = results[0]
        ttl = results[1]

        limit = settings.rate_limit_per_minute
        reset = max(ttl, 0)

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": str(reset),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                },
            )

        logger.debug(
            f"Rate limit: {count}/{limit} for {user_id}, reset in {reset}s"
        )

    except HTTPException:
        raise
    except Exception as e:
        # Redis is down — gracefully degrade, skip rate limiting
        logger.warning(f"Rate limiting skipped (Redis unavailable): {e}")
