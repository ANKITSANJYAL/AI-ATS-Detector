"""
API v1 router.
Aggregates all v1 endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import billing, documents, history, jobs, webhooks

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"],
)

api_router.include_router(
    history.router,
    prefix="/history",
    tags=["history"],
)

api_router.include_router(
    billing.router,
    prefix="/billing",
    tags=["billing"],
)

api_router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["jobs"],
)

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"],
)
