"""
Job description endpoints.
Handles job description management with PostgreSQL persistence.
"""
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, verify_rate_limit
from app.core.logging import get_logger
from app.db.models import JobDescription
from app.db.session import get_db_session
from app.models.schemas import JobDescriptionRequest, JobDescriptionResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create job description",
    description="""
    Store a job description for ATS scoring analysis.

    **Required fields:**
    - title: Job title
    - company: Company name
    - description: Full job description text

    **Optional fields:**
    - required_skills: List of required skills
    - preferred_skills: List of preferred/nice-to-have skills
    """,
)
async def create_job_description(
    request: JobDescriptionRequest,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    _: Annotated[None, Depends(verify_rate_limit)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> JobDescriptionResponse:
    """Create and store job description."""
    job_row = JobDescription(
        user_id=user_id,
        title=request.title,
        company=request.company,
        description=request.description,
        required_skills=request.required_skills,
        preferred_skills=request.preferred_skills,
    )
    db.add(job_row)
    await db.flush()

    logger.info(f"Job description created: {job_row.id} by user {user_id}")

    return JobDescriptionResponse(
        job_id=str(job_row.id),
        created_at=job_row.created_at or datetime.now(UTC),
    )


@router.get(
    "/{job_id}",
    response_model=JobDescriptionRequest,
    status_code=status.HTTP_200_OK,
    summary="Get job description",
    description="Retrieve a previously stored job description by ID",
)
async def get_job_description(
    job_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> JobDescriptionRequest:
    """Retrieve job description by ID."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        ) from None

    stmt = select(JobDescription).where(
        JobDescription.id == job_uuid,
        JobDescription.user_id == user_id,
    )
    result = await db.execute(stmt)
    job_row = result.scalar_one_or_none()

    if not job_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found or access denied",
        )

    return JobDescriptionRequest(
        title=job_row.title,
        company=job_row.company,
        description=job_row.description,
        required_skills=job_row.required_skills or [],
        preferred_skills=job_row.preferred_skills or [],
    )
