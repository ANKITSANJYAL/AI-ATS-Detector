"""
History endpoints.
Fetch past detection and ATS scoring results for the authenticated user.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.core.logging import get_logger
from app.db.models import ATSResult, DetectionResult, Document, JobDescription
from app.db.session import get_db_session

logger = get_logger(__name__)

router = APIRouter()


# ---------- Response schemas ----------

class DetectionHistoryItem(BaseModel):
    id: str
    document_id: str
    filename: str
    detection_result: str
    confidence_score: float
    ai_probability: float
    created_at: str


class ATSHistoryItem(BaseModel):
    id: str
    document_id: str
    filename: str
    job_title: str
    overall_score: float
    keyword_match_score: float
    semantic_similarity_score: float
    format_score: float
    created_at: str


class HistoryResponse(BaseModel):
    detections: list[DetectionHistoryItem]
    ats_scores: list[ATSHistoryItem]
    total_detections: int
    total_ats: int


# ---------- Endpoints ----------

@router.get(
    "/",
    response_model=HistoryResponse,
    summary="Fetch analysis history",
    description="Returns past AI detection and ATS scoring results for the current user.",
)
async def get_history(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=50, ge=1, le=200, description="Max results per category"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> HistoryResponse:
    """Return recent analysis history for the authenticated user."""

    # --- Detection history ---
    det_stmt = (
        select(DetectionResult, Document.filename)
        .join(Document, DetectionResult.document_id == Document.id)
        .where(DetectionResult.user_id == user_id)
        .order_by(DetectionResult.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    det_rows = (await db.execute(det_stmt)).all()

    det_count_stmt = (
        select(func.count())
        .select_from(DetectionResult)
        .where(DetectionResult.user_id == user_id)
    )
    total_detections = (await db.execute(det_count_stmt)).scalar() or 0

    detections = [
        DetectionHistoryItem(
            id=str(row.DetectionResult.id),
            document_id=str(row.DetectionResult.document_id),
            filename=row.filename,
            detection_result=row.DetectionResult.detection_result,
            confidence_score=row.DetectionResult.confidence_score,
            ai_probability=row.DetectionResult.ai_probability,
            created_at=row.DetectionResult.created_at.isoformat(),
        )
        for row in det_rows
    ]

    # --- ATS history ---
    ats_stmt = (
        select(ATSResult, Document.filename, JobDescription.title)
        .join(Document, ATSResult.document_id == Document.id)
        .join(JobDescription, ATSResult.job_id == JobDescription.id)
        .where(ATSResult.user_id == user_id)
        .order_by(ATSResult.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    ats_rows = (await db.execute(ats_stmt)).all()

    ats_count_stmt = (
        select(func.count())
        .select_from(ATSResult)
        .where(ATSResult.user_id == user_id)
    )
    total_ats = (await db.execute(ats_count_stmt)).scalar() or 0

    ats_scores = [
        ATSHistoryItem(
            id=str(row.ATSResult.id),
            document_id=str(row.ATSResult.document_id),
            filename=row.filename,
            job_title=row.title or "(untitled)",
            overall_score=row.ATSResult.overall_score,
            keyword_match_score=row.ATSResult.keyword_match_score,
            semantic_similarity_score=row.ATSResult.semantic_similarity_score,
            format_score=row.ATSResult.format_score,
            created_at=row.ATSResult.created_at.isoformat(),
        )
        for row in ats_rows
    ]

    return HistoryResponse(
        detections=detections,
        ats_scores=ats_scores,
        total_detections=total_detections,
        total_ats=total_ats,
    )
