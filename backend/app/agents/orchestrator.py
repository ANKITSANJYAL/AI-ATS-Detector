"""
Orchestrator Agent.
Coordinates multiple agents and manages workflow.
"""

from app.agents.ats_scorer import ATSScorerAgent, get_ats_scorer_agent
from app.agents.detector import DetectorAgent, get_detector_agent
from app.core.logging import get_logger
from app.models.schemas import (
    AIDetectionResponse,
    ATSScoringResponse,
)
from app.services.document_processor import DocumentProcessor, get_document_processor

logger = get_logger(__name__)


class OrchestratorAgent:
    """
    Orchestrator agent for coordinating analysis workflows.
    Manages document processing and agent coordination.
    """

    def __init__(
        self,
        detector_agent: DetectorAgent | None = None,
        ats_scorer_agent: ATSScorerAgent | None = None,
        document_processor: DocumentProcessor | None = None,
    ):
        """Initialize orchestrator agent."""
        self.detector_agent = detector_agent or get_detector_agent()
        self.ats_scorer_agent = ats_scorer_agent or get_ats_scorer_agent()
        self.document_processor = document_processor or get_document_processor()

    async def process_document_for_detection(
        self,
        document_id: str,
        file_content: bytes,
        mime_type: str,
    ) -> AIDetectionResponse:
        """
        Process document for AI detection.

        Args:
            document_id: Document identifier
            file_content: Document binary content
            mime_type: Document MIME type

        Returns:
            AI detection analysis results
        """
        logger.info(f"Orchestrating AI detection for document {document_id}")

        # Extract text (plain)
        text = await self.document_processor.extract_text(file_content, mime_type)
        text = self.document_processor.preprocess_text(text)

        # Extract structured blocks (with formatting)
        try:
            structured_blocks = await self.document_processor.extract_structured_text(
                file_content, mime_type
            )
            logger.info(f"Extracted {len(structured_blocks)} structured blocks")
        except Exception as e:
            logger.warning(f"Structured extraction failed: {e}, using plain text")
            structured_blocks = []

        # Perform detection with structured data
        result = await self.detector_agent.analyze(
            document_id,
            text,
            structured_blocks=structured_blocks
        )

        return result

    async def process_resume_for_ats(
        self,
        document_id: str,
        job_id: str,
        file_content: bytes,
        mime_type: str,
        job_description: dict,
    ) -> ATSScoringResponse:
        """
        Process resume for ATS scoring.

        Args:
            document_id: Resume document identifier
            job_id: Job description identifier
            file_content: Resume binary content
            mime_type: Resume MIME type
            job_description: Job description data

        Returns:
            ATS scoring analysis results
        """
        logger.info(f"Orchestrating ATS scoring for document {document_id}")

        # Extract text
        text = await self.document_processor.extract_text(file_content, mime_type)
        text = self.document_processor.preprocess_text(text)

        # Perform ATS scoring
        result = await self.ats_scorer_agent.analyze(
            document_id,
            job_id,
            text,
            job_description,
        )

        return result

    async def health_check(self) -> dict[str, bool]:
        """Check health of all agents and services with real checks."""
        from app.db.session import get_engine
        from app.services.ai_classifier import get_ai_classifier
        from app.services.redis_client import get_redis_client

        results: dict[str, bool] = {}

        # Check detector agent (are ML models loaded?)
        try:
            classifier = get_ai_classifier()
            results["detector_agent"] = classifier._loaded and len(classifier._models) > 0
        except Exception:
            results["detector_agent"] = False

        # Check ATS scorer agent (has LLM client?)
        try:
            results["ats_scorer_agent"] = self.ats_scorer_agent is not None
        except Exception:
            results["ats_scorer_agent"] = False

        # Check document processor
        try:
            results["document_processor"] = self.document_processor is not None
        except Exception:
            results["document_processor"] = False

        # Check database connectivity
        try:
            engine = get_engine()
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            results["database"] = True
        except Exception:
            results["database"] = False

        # Check Redis connectivity
        try:
            redis = await get_redis_client()
            results["redis"] = await redis.ping()
        except Exception:
            results["redis"] = False

        return results


# ── Singleton ──────────────────────────────────────────────────────────
_orchestrator_agent: OrchestratorAgent | None = None


def get_orchestrator_agent() -> OrchestratorAgent:
    """Return a singleton OrchestratorAgent."""
    global _orchestrator_agent
    if _orchestrator_agent is None:
        _orchestrator_agent = OrchestratorAgent()
    return _orchestrator_agent
