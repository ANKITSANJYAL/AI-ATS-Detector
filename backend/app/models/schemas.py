"""
Pydantic models for request/response schemas.
All models include Field descriptions for self-documenting API.
"""
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# Enums
class DocumentType(str, Enum):
    """Document type enumeration."""
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    GENERAL = "general"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DetectionResult(str, Enum):
    """AI detection result."""
    HUMAN = "human"
    AI_GENERATED = "ai_generated"
    MIXED = "mixed"


# Base Schemas
class DocumentUploadRequest(BaseModel):
    """Request schema for document upload."""

    document_type: DocumentType = Field(
        description="Type of document being uploaded"
    )
    filename: str = Field(
        description="Original filename",
        min_length=1,
        max_length=255
    )


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""

    document_id: str = Field(description="Unique document identifier")
    upload_url: str = Field(description="Presigned URL for document upload")
    expires_at: datetime = Field(description="Upload URL expiration timestamp")


# AI Detection Schemas
class AIDetectionRequest(BaseModel):
    """Request schema for AI content detection."""

    document_id: str = Field(description="Document ID to analyze")


class LinguisticFeatures(BaseModel):
    """Linguistic features extracted during forensic analysis."""

    sentence_complexity: float = Field(
        description="Average sentence complexity score (0-1)",
        ge=0.0,
        le=1.0
    )
    vocabulary_diversity: float = Field(
        description="Lexical diversity score (0-1)",
        ge=0.0,
        le=1.0
    )
    coherence_score: float = Field(
        description="Text coherence and flow score (0-1)",
        ge=0.0,
        le=1.0
    )
    transition_patterns: float = Field(
        description="Natural transition pattern score (0-1)",
        ge=0.0,
        le=1.0
    )
    stylistic_consistency: float = Field(
        description="Writing style consistency score (0-1)",
        ge=0.0,
        le=1.0
    )
    burstiness_score: float = Field(
        default=0.5,
        description="Burstiness score (0-1). High = bursty/human-like variation in sentence length. Low = uniform/AI-like.",
        ge=0.0,
        le=1.0
    )


class AIDetectionResponse(BaseModel):
    """Response schema for AI detection analysis."""

    document_id: str = Field(description="Analyzed document ID")
    detection_result: DetectionResult = Field(
        description="Overall detection result"
    )
    confidence_score: float = Field(
        description="Confidence in detection (0-1)",
        ge=0.0,
        le=1.0
    )
    ai_probability: float = Field(
        description="Probability content is AI-generated (0-1)",
        ge=0.0,
        le=1.0
    )
    linguistic_features: LinguisticFeatures = Field(
        description="Detailed linguistic analysis"
    )
    flagged_sections: list[str] = Field(
        description="Text sections flagged as potentially AI-generated",
        default_factory=list
    )
    sentence_analysis: list[dict] = Field(
        description="Sentence-by-sentence AI detection analysis",
        default_factory=list
    )
    structured_blocks: list[dict] = Field(
        description="Document structure with formatting metadata",
        default_factory=list
    )
    detailed_analysis: list[str] = Field(
        description="Detailed explanation of detection results",
        default_factory=list
    )
    model_versions: dict[str, str] = Field(
        description="Model name to version mapping used for this analysis",
        default_factory=dict
    )
    analysis_timestamp: datetime = Field(
        description="When analysis was performed"
    )


# ATS Scoring Schemas
class JobDescriptionRequest(BaseModel):
    """Request schema for job description submission."""

    title: str = Field(
        description="Job title",
        min_length=1,
        max_length=255
    )
    company: str = Field(
        description="Company name",
        min_length=1,
        max_length=255
    )
    description: str = Field(
        description="Full job description text",
        min_length=50
    )
    required_skills: list[str] = Field(
        description="Required skills and qualifications",
        default_factory=list
    )
    preferred_skills: list[str] = Field(
        description="Preferred/nice-to-have skills",
        default_factory=list
    )


class JobDescriptionResponse(BaseModel):
    """Response schema for job description storage."""

    job_id: str = Field(description="Unique job description identifier")
    created_at: datetime = Field(description="Creation timestamp")


class ATSScoringRequest(BaseModel):
    """Request schema for ATS scoring analysis."""

    document_id: str = Field(description="Resume document ID")
    job_id: str | None = Field(default=None, description="Job description ID (if pre-stored)")
    job_description: str | None = Field(default=None, description="Raw job description text")
    job_url: str | None = Field(default=None, description="Job posting URL")

    @model_validator(mode="after")
    def validate_job_source(self):
        """Ensure at least one job source is provided."""
        if not any([self.job_id, self.job_description, self.job_url]):
            raise ValueError("Must provide job_id, job_description, or job_url")
        return self


class SkillMatch(BaseModel):
    """Individual skill match details."""

    skill: str = Field(description="Skill name")
    matched: bool = Field(description="Whether skill was found in resume")
    relevance: float = Field(
        description="Relevance score for this skill (0-1)",
        ge=0.0,
        le=1.0
    )


class GapAnalysis(BaseModel):
    """Skills gap analysis."""

    missing_required_skills: list[str] = Field(
        description="Required skills not found in resume"
    )
    missing_preferred_skills: list[str] = Field(
        description="Preferred skills not found in resume"
    )
    recommendations: list[str] = Field(
        description="Actionable recommendations to improve match"
    )


class ATSScoringResponse(BaseModel):
    """Response schema for ATS scoring analysis."""

    document_id: str = Field(description="Analyzed resume document ID")
    job_id: str = Field(description="Job description ID")
    overall_score: float = Field(
        description="Overall ATS compatibility score (0-100)",
        ge=0.0,
        le=100.0
    )
    keyword_match_score: float = Field(
        description="Keyword matching score (0-100)",
        ge=0.0,
        le=100.0
    )
    semantic_similarity_score: float = Field(
        description="Semantic similarity score (0-100)",
        ge=0.0,
        le=100.0
    )
    format_score: float = Field(
        description="Resume format and structure score (0-100)",
        ge=0.0,
        le=100.0
    )
    skill_matches: list[SkillMatch] = Field(
        description="Detailed skill matching analysis"
    )
    gap_analysis: GapAnalysis = Field(
        description="Skills gap and improvement recommendations"
    )
    analysis_timestamp: datetime = Field(
        description="When analysis was performed"
    )


# Background Job Schemas
class JobStatusResponse(BaseModel):
    """Response schema for async job status."""

    job_id: str = Field(description="Background job identifier")
    status: ProcessingStatus = Field(description="Current processing status")
    progress: float = Field(
        description="Processing progress (0-100)",
        ge=0.0,
        le=100.0
    )
    result: AIDetectionResponse | ATSScoringResponse | None = Field(
        description="Analysis result (when completed)",
        default=None
    )
    error: str | None = Field(
        description="Error message (when failed)",
        default=None
    )


# Billing Schemas
class UsageRecord(BaseModel):
    """Usage record for metered billing."""

    user_id: str = Field(description="User identifier")
    feature: Literal["ai_detection", "ats_scoring"] = Field(
        description="Feature used"
    )
    quantity: int = Field(
        description="Usage quantity (typically 1 per analysis)",
        ge=1
    )
    timestamp: datetime = Field(description="Usage timestamp")


class BillingWebhookEvent(BaseModel):
    """Stripe webhook event payload."""

    event_type: str = Field(description="Stripe event type")
    data: dict = Field(description="Event data payload")


# AI Humanizer Schemas
class HumanizeSentenceRequest(BaseModel):
    """Request to humanize a single AI-flagged sentence."""

    sentence: str = Field(description="The AI-flagged sentence to rewrite", min_length=5)
    context_before: str = Field(default="", description="1-2 sentences before for context")
    context_after: str = Field(default="", description="1-2 sentences after for context")
    tone: Literal["natural", "casual", "professional", "academic"] = Field(
        default="natural", description="Desired writing tone"
    )


class HumanizeBatchRequest(BaseModel):
    """Request to humanize multiple AI-flagged sentences."""

    document_id: str = Field(description="Source document ID")
    sentences: list[dict] = Field(
        description="List of sentences with 'text', 'index', optional 'context_before'/'context_after'",
        min_length=1,
    )
    tone: Literal["natural", "casual", "professional", "academic"] = Field(
        default="natural", description="Desired writing tone"
    )


class RewriteOption(BaseModel):
    """A single rewrite suggestion."""

    text: str = Field(description="Rewritten sentence text")
    approach: str = Field(description="Brief label for the approach used")


class HumanizeResponse(BaseModel):
    """Response for a single sentence humanization."""

    original_text: str = Field(description="The original AI-flagged sentence")
    rewrites: list[RewriteOption] = Field(description="Alternative human-sounding rewrites")
    explanation: str = Field(description="Why the original sounds AI-generated")
    ai_tells: list[str] = Field(
        description="Specific AI writing patterns detected",
        default_factory=list,
    )


class HumanizeBatchResponse(BaseModel):
    """Response for batch humanization."""

    document_id: str = Field(description="Source document ID")
    results: list[HumanizeResponse] = Field(description="Per-sentence humanization results")
    tone: str = Field(description="Tone used for rewrites")


# Resume Optimizer Schemas
class ResumeOptimizeRequest(BaseModel):
    """Request to generate an ATS-optimized resume."""

    document_id: str = Field(description="Resume document ID")
    job_id: str = Field(description="Job description ID (from previous ATS scoring)")


class DiffStats(BaseModel):
    """Statistics about what changed between original and optimized."""

    words_added: int = Field(description="Number of new words added")
    words_removed: int = Field(description="Number of words removed")
    original_line_count: int = Field(description="Lines in original")
    optimized_line_count: int = Field(description="Lines in optimized")
    original_word_count: int = Field(description="Words in original")
    optimized_word_count: int = Field(description="Words in optimized")


class ChangeItem(BaseModel):
    """A single change made during optimization."""

    section: str = Field(description="Resume section affected")
    change: str = Field(description="What was changed")
    reason: str = Field(description="Why this helps ATS compatibility")


class SectionImprovement(BaseModel):
    """Before/after comparison for a resume section."""

    section: str = Field(description="Section name")
    before: str = Field(description="Original text snippet")
    after: str = Field(description="Optimized text snippet")
    impact: Literal["high", "medium", "low"] = Field(description="Expected impact level")


class ResumeOptimizeResponse(BaseModel):
    """Response containing the optimized resume."""

    document_id: str = Field(description="Original resume document ID")
    job_id: str = Field(description="Job description ID")
    optimized_resume: str = Field(description="Full optimized resume text")
    changes: list[ChangeItem] = Field(description="List of changes made")
    section_improvements: list[SectionImprovement] = Field(
        description="Section-by-section before/after comparisons"
    )
    keywords_added: list[str] = Field(description="Keywords injected into the resume")
    estimated_score_improvement: int = Field(
        description="Estimated ATS score improvement (points)"
    )
    diff_stats: DiffStats = Field(description="Statistics about what changed")
    generated_at: datetime = Field(description="When optimization was generated")


# Health Check Schemas
class HealthCheckResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="Overall system health status"
    )
    version: str = Field(description="API version")
    timestamp: datetime = Field(description="Health check timestamp")
    services: dict[str, bool] = Field(
        description="Individual service health status"
    )
