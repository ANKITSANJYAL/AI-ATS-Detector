"""
SQLAlchemy ORM models for PostgreSQL persistence.
Defines the schema for documents, jobs, analysis results, and billing.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Document(Base):
    """Uploaded document with binary content and metadata."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False, default="resume")
    mime_type = Column(String(100), nullable=False)
    content = Column(LargeBinary, nullable=False)
    text_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    detection_results = relationship("DetectionResult", back_populates="document", cascade="all, delete-orphan")
    ats_results = relationship("ATSResult", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_user_created", "user_id", "created_at"),
    )


class JobDescription(Base):
    """Stored job description for ATS scoring."""

    __tablename__ = "job_descriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    required_skills = Column(JSON, default=list)
    preferred_skills = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    ats_results = relationship("ATSResult", back_populates="job_description", cascade="all, delete-orphan")


class DetectionResult(Base):
    """AI detection analysis result."""

    __tablename__ = "detection_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    detection_result = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    ai_probability = Column(Float, nullable=False)
    linguistic_features = Column(JSON, nullable=False)
    flagged_sections = Column(JSON, default=list)
    sentence_analysis = Column(JSON, default=list)
    structured_blocks = Column(JSON, default=list)
    detailed_analysis = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    document = relationship("Document", back_populates="detection_results")


class ATSResult(Base):
    """ATS scoring analysis result."""

    __tablename__ = "ats_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    overall_score = Column(Float, nullable=False)
    keyword_match_score = Column(Float, nullable=False)
    semantic_similarity_score = Column(Float, nullable=False)
    format_score = Column(Float, nullable=False)
    skill_matches = Column(JSON, default=list)
    gap_analysis = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    document = relationship("Document", back_populates="ats_results")
    job_description = relationship("JobDescription", back_populates="ats_results")


class UsageRecord(Base):
    """Billable usage event for Stripe metered billing."""

    __tablename__ = "usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    feature = Column(String(50), nullable=False)  # "ai_detection" | "ats_scoring"
    endpoint = Column(String(255), nullable=False)
    status_code = Column(String(10), nullable=False)
    duration_ms = Column(Float, nullable=False)
    reported_to_stripe = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("ix_usage_user_feature", "user_id", "feature"),
        Index("ix_usage_unreported", "reported_to_stripe", "created_at"),
    )
