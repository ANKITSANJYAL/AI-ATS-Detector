"""
Document analysis endpoints.
Handles document upload and analysis operations.
Persists all data to PostgreSQL; uses Redis only for caching.
"""
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import OrchestratorAgent, get_orchestrator_agent
from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user_id, verify_rate_limit
from app.core.logging import get_logger
from app.core.sanitize import sanitize_filename
from app.db.models import ATSResult, DetectionResult, Document, JobDescription
from app.db.session import get_db_session
from app.models.schemas import (
    AIDetectionRequest,
    AIDetectionResponse,
    ATSScoringRequest,
    ATSScoringResponse,
    DocumentType,
    DocumentUploadResponse,
    HumanizeBatchRequest,
    HumanizeBatchResponse,
    HumanizeResponse,
    HumanizeSentenceRequest,
    ResumeOptimizeRequest,
    ResumeOptimizeResponse,
)
from app.services.redis_client import RedisClient, get_redis_client

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document for analysis",
    description="""
    Upload a document (PDF or DOCX) for analysis.

    **Supported formats:**
    - PDF (.pdf)
    - Microsoft Word (.docx)
    - Plain text (.txt)

    **Max file size:** 10 MB
    """,
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Document file to upload")],
    document_type: Annotated[DocumentType, Form(description="Type of document")] = DocumentType.RESUME,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    _: Annotated[None, Depends(verify_rate_limit)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> DocumentUploadResponse:
    """Upload document and persist to database."""
    # Validate file type
    if file.content_type not in settings.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    # Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    max_size = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.max_file_size_mb}MB",
        )

    content = await file.read()
    document_id = uuid.uuid4()

    # Sanitize filename to prevent stored XSS
    safe_filename = sanitize_filename(file.filename or "upload")

    # Persist to PostgreSQL
    doc = Document(
        id=document_id,
        user_id=user_id,
        filename=safe_filename,
        document_type=document_type.value,
        mime_type=file.content_type,
        content=content,
    )
    db.add(doc)
    await db.flush()

    logger.info(f"Document uploaded: {document_id} by user {user_id}")

    return DocumentUploadResponse(
        document_id=str(document_id),
        upload_url=f"/api/v1/documents/{document_id}",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )


@router.post(
    "/detect",
    response_model=AIDetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect AI-generated content",
    description="""
    Perform forensic linguistic analysis to detect AI-generated content.

    **Analysis includes:**
    - Sentence complexity patterns
    - Vocabulary diversity
    - Coherence and flow
    - Transition patterns
    - Stylistic consistency

    **Returns:** Detailed detection report with confidence scores
    """,
)
async def detect_ai_content(
    request: AIDetectionRequest,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    _: Annotated[None, Depends(verify_rate_limit)] = None,
    orchestrator: Annotated[OrchestratorAgent, Depends(get_orchestrator_agent)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
    redis: Annotated[RedisClient, Depends(get_redis_client)] = None,
) -> AIDetectionResponse:
    """Analyze document for AI-generated content."""
    document_id = request.document_id

    # Check cache first
    cache_key = f"result:detection:{document_id}"
    cached = await redis.get(cache_key)
    if cached:
        logger.info(f"Cache hit for detection {document_id}")
        return AIDetectionResponse.model_validate_json(cached)

    # Load document from database
    doc = await _get_user_document(db, document_id, user_id)

    logger.info(f"Starting AI detection for document {document_id}")

    result = await orchestrator.process_document_for_detection(
        document_id,
        doc.content,
        doc.mime_type,
    )

    # Persist result to PostgreSQL
    detection_row = DetectionResult(
        document_id=doc.id,
        user_id=user_id,
        detection_result=result.detection_result.value,
        confidence_score=result.confidence_score,
        ai_probability=result.ai_probability,
        linguistic_features=result.linguistic_features.model_dump(),
        flagged_sections=result.flagged_sections,
        sentence_analysis=result.sentence_analysis,
        structured_blocks=result.structured_blocks,
        detailed_analysis=result.detailed_analysis,
    )
    db.add(detection_row)
    await db.flush()

    # Cache for 24 hours
    await redis.set(cache_key, result.model_dump_json(), ttl=86400)

    logger.info(f"AI detection completed for {document_id}: {result.detection_result.value}")
    return result


@router.post(
    "/score",
    response_model=ATSScoringResponse,
    status_code=status.HTTP_200_OK,
    summary="Score resume against job description",
    description="""
    Analyze resume compatibility with job description using ATS scoring.

    **Analysis includes:**
    - Keyword matching
    - Semantic similarity
    - Format optimization
    - Skills gap analysis

    **Returns:** Comprehensive scoring report with improvement recommendations
    """,
)
async def score_resume(
    request: ATSScoringRequest,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    _: Annotated[None, Depends(verify_rate_limit)] = None,
    orchestrator: Annotated[OrchestratorAgent, Depends(get_orchestrator_agent)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
    redis: Annotated[RedisClient, Depends(get_redis_client)] = None,
) -> ATSScoringResponse:
    """Score resume against job description."""
    document_id = request.document_id

    # Load document from database
    doc = await _get_user_document(db, document_id, user_id)

    # Resolve job description
    job_id: str
    job_data: dict

    if request.job_id:
        # Use existing job from database
        stmt = select(JobDescription).where(
            JobDescription.id == uuid.UUID(request.job_id),
            JobDescription.user_id == user_id,
        )
        result = await db.execute(stmt)
        job_row = result.scalar_one_or_none()
        if not job_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job description not found",
            )
        job_id = str(job_row.id)
        job_data = {
            "description": job_row.description,
            "url": job_row.url or "",
            "required_skills": job_row.required_skills or [],
            "preferred_skills": job_row.preferred_skills or [],
        }
    else:
        # Create job from raw text or URL
        job_description_text = request.job_description or ""

        if request.job_url and not job_description_text:
            job_description_text = await _fetch_job_url(request.job_url)

        if not job_description_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract job description from provided source",
            )

        # Extract skills using LLM
        from app.agents.ats_scorer import get_ats_scorer_agent
        ats_scorer = get_ats_scorer_agent()
        skills_data = await ats_scorer.extract_skills_from_job(job_description_text)

        # Persist job to database
        job_row = JobDescription(
            user_id=user_id,
            title="(from URL)" if request.job_url else "(pasted)",
            company="Unknown",
            description=job_description_text,
            url=request.job_url or None,
            required_skills=skills_data.get("required_skills", []),
            preferred_skills=skills_data.get("preferred_skills", []),
        )
        db.add(job_row)
        await db.flush()

        job_id = str(job_row.id)
        job_data = {
            "description": job_description_text,
            "url": request.job_url or "",
            "required_skills": job_row.required_skills,
            "preferred_skills": job_row.preferred_skills,
        }

        logger.info(
            f"Job created with {len(job_data['required_skills'])} required "
            f"and {len(job_data['preferred_skills'])} preferred skills"
        )

    # Check cache
    cache_key = f"result:ats:{document_id}:{job_id}"
    cached = await redis.get(cache_key)
    if cached:
        logger.info(f"Cache hit for ATS {document_id}:{job_id}")
        return ATSScoringResponse.model_validate_json(cached)

    logger.info(f"Starting ATS scoring for document {document_id} against job {job_id}")

    result = await orchestrator.process_resume_for_ats(
        document_id, job_id, doc.content, doc.mime_type, job_data,
    )

    # Persist to database
    ats_row = ATSResult(
        document_id=doc.id,
        job_id=uuid.UUID(job_id),
        user_id=user_id,
        overall_score=result.overall_score,
        keyword_match_score=result.keyword_match_score,
        semantic_similarity_score=result.semantic_similarity_score,
        format_score=result.format_score,
        skill_matches=[sm.model_dump() for sm in result.skill_matches],
        gap_analysis=result.gap_analysis.model_dump(),
    )
    db.add(ats_row)
    await db.flush()

    # Cache for 24 hours
    await redis.set(cache_key, result.model_dump_json(), ttl=86400)

    logger.info(f"ATS scoring completed for {document_id}: {result.overall_score:.1f}/100")
    return result


@router.post(
    "/humanize",
    response_model=HumanizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Humanize a single AI-flagged sentence",
    description="""
    Rewrite an AI-flagged sentence to sound more human.

    **Returns:** 3 alternative rewrites with different approaches,
    an explanation of why the original sounds AI-generated,
    and specific AI writing patterns detected.
    """,
)
async def humanize_sentence(
    request: HumanizeSentenceRequest,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    _: Annotated[None, Depends(verify_rate_limit)] = None,
) -> HumanizeResponse:
    """Generate human-sounding rewrites for an AI-flagged sentence."""
    from app.agents.humanizer import get_humanizer_agent

    humanizer = get_humanizer_agent()

    logger.info(f"Humanizing sentence for user {user_id}, tone={request.tone}")

    result = await humanizer.humanize_sentence(
        sentence=request.sentence,
        context_before=request.context_before,
        context_after=request.context_after,
        tone=request.tone,
    )

    return HumanizeResponse(**result)


@router.post(
    "/humanize-batch",
    response_model=HumanizeBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Humanize multiple AI-flagged sentences",
    description="""
    Rewrite multiple AI-flagged sentences in batch.
    Maximum 20 sentences per request.

    **Returns:** Per-sentence humanization results.
    """,
)
async def humanize_batch(
    request: HumanizeBatchRequest,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    _: Annotated[None, Depends(verify_rate_limit)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> HumanizeBatchResponse:
    """Humanize multiple AI-flagged sentences in batch."""
    from app.agents.humanizer import get_humanizer_agent

    # Verify document belongs to user
    await _get_user_document(db, request.document_id, user_id)

    humanizer = get_humanizer_agent()

    logger.info(
        f"Batch humanizing {len(request.sentences)} sentences for "
        f"document {request.document_id}"
    )

    sentences = [
        {
            "text": s.get("text", ""),
            "context_before": s.get("context_before", ""),
            "context_after": s.get("context_after", ""),
        }
        for s in request.sentences
    ]

    raw_results = await humanizer.humanize_batch(
        sentences=sentences,
        tone=request.tone,
    )

    results = [HumanizeResponse(**r) for r in raw_results]

    return HumanizeBatchResponse(
        document_id=request.document_id,
        results=results,
        tone=request.tone,
    )


@router.post(
    "/optimize-resume",
    response_model=ResumeOptimizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate ATS-optimized resume",
    description="""
    Generate a tailored, ATS-optimized version of the resume
    for a specific job description.

    **Requires:** A previous ATS scoring run (document_id + job_id).

    **Returns:** Optimized resume text, change list,
    section-by-section comparisons, and diff statistics.
    """,
)
async def optimize_resume(
    request: ResumeOptimizeRequest,
    user_id: Annotated[str, Depends(get_current_user_id)] = None,
    _: Annotated[None, Depends(verify_rate_limit)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
    redis: Annotated[RedisClient, Depends(get_redis_client)] = None,
    orchestrator: Annotated[OrchestratorAgent, Depends(get_orchestrator_agent)] = None,
) -> ResumeOptimizeResponse:
    """Generate an ATS-optimized resume from a previous scoring run."""
    from datetime import UTC, datetime

    from app.agents.resume_optimizer import get_resume_optimizer_agent

    document_id = request.document_id
    job_id = request.job_id

    # Check cache
    cache_key = f"result:optimize:{document_id}:{job_id}"
    cached = await redis.get(cache_key)
    if cached:
        logger.info(f"Cache hit for optimization {document_id}:{job_id}")
        return ResumeOptimizeResponse.model_validate_json(cached)

    # Load document
    doc = await _get_user_document(db, document_id, user_id)

    # Load ATS result for this document+job pair
    stmt = select(ATSResult).where(
        ATSResult.document_id == doc.id,
        ATSResult.job_id == uuid.UUID(job_id),
        ATSResult.user_id == user_id,
    )
    ats_exec = await db.execute(stmt)
    ats_row = ats_exec.scalar_one_or_none()
    if not ats_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ATS scoring result found for this document/job. Run /score first.",
        )

    # Load job description
    stmt = select(JobDescription).where(
        JobDescription.id == uuid.UUID(job_id),
        JobDescription.user_id == user_id,
    )
    job_exec = await db.execute(stmt)
    job_row = job_exec.scalar_one_or_none()
    if not job_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )

    # Extract resume text
    from app.services.document_processor import DocumentProcessor
    processor = DocumentProcessor()
    resume_text = processor.extract_text(doc.content, doc.mime_type)

    optimizer = get_resume_optimizer_agent()

    logger.info(f"Optimizing resume {document_id} for job {job_id}")

    result = await optimizer.optimize(
        resume_text=resume_text,
        job_description=job_row.description,
        skill_matches=ats_row.skill_matches or [],
        gap_analysis=ats_row.gap_analysis or {},
        format_score=ats_row.format_score if hasattr(ats_row, "format_score") else 50,
        keyword_score=ats_row.keyword_match_score if hasattr(ats_row, "keyword_match_score") else 50,
    )

    response = ResumeOptimizeResponse(
        document_id=document_id,
        job_id=job_id,
        optimized_resume=result["optimized_resume"],
        changes=[
            {"section": c.get("section", ""), "change": c.get("change", ""), "reason": c.get("reason", "")}
            for c in result.get("changes", [])
        ],
        section_improvements=[
            {
                "section": si.get("section", ""),
                "before": si.get("before", ""),
                "after": si.get("after", ""),
                "impact": si.get("impact", "medium"),
            }
            for si in result.get("section_improvements", [])
        ],
        keywords_added=result.get("keywords_added", []),
        estimated_score_improvement=result.get("estimated_score_improvement", 0),
        diff_stats=result.get("diff_stats", {
            "words_added": 0, "words_removed": 0,
            "original_line_count": 0, "optimized_line_count": 0,
            "original_word_count": 0, "optimized_word_count": 0,
        }),
        generated_at=datetime.now(UTC),
    )

    # Cache for 12 hours
    await redis.set(cache_key, response.model_dump_json(), ttl=43200)

    logger.info(f"Resume optimization completed for {document_id}")
    return response


# --- Helper functions ---

async def _get_user_document(db: AsyncSession, document_id: str, user_id: str) -> Document:
    """Load and verify ownership of a document."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID") from None

    stmt = select(Document).where(Document.id == doc_uuid, Document.user_id == user_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied",
        )
    return doc


async def _fetch_job_url(job_url: str) -> str:
    """Fetch job description from a URL, handling bot protection gracefully."""
    logger.info(f"Fetching job description from URL: {job_url}")

    try:
        from app.services.web_scraper import WebScraper
        scraper = WebScraper()
        text = await scraper.fetch_url(job_url, timeout=60000)

        block_indicators = [
            "cloudflare", "just a moment", "verification required",
            "browser extension", "blocked", "ray id",
        ]
        if any(ind in text.lower() for ind in block_indicators) or len(text) < 300:
            raise ValueError("Site is blocking automated access")

        logger.info(f"Successfully fetched {len(text)} characters")
        return text

    except Exception as fetch_error:
        logger.error(f"Failed to fetch URL: {fetch_error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "url_fetch_blocked",
                "message": "The job site is blocking automated access. Please copy and paste the job description instead.",
                "instructions": [
                    "1. Open the job posting in your browser",
                    "2. Select and copy the job description text",
                    "3. Paste it in the 'Job Description' field below",
                    "4. Click 'Analyze Resume' again",
                ],
                "reason": str(fetch_error),
            },
        ) from fetch_error
