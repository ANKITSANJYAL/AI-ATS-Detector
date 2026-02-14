"""
Contract tests for API response schemas.
Validates that all API responses match their declared Pydantic models,
ensuring frontend-backend contract compliance.
"""
import pytest
from datetime import UTC, datetime

from app.models.schemas import (
    AIDetectionResponse,
    ATSScoringResponse,
    DocumentUploadResponse,
    HealthCheckResponse,
    LinguisticFeatures,
    DetectionResult,
    GapAnalysis,
    SkillMatch,
)


class TestAIDetectionResponseContract:
    """Validate AIDetectionResponse schema contract."""

    def _make_valid_response(self, **overrides) -> dict:
        """Create a valid response payload."""
        base = {
            "document_id": "abc-123",
            "detection_result": "human",
            "confidence_score": 0.85,
            "ai_probability": 0.15,
            "linguistic_features": {
                "sentence_complexity": 0.7,
                "vocabulary_diversity": 0.6,
                "coherence_score": 0.5,
                "transition_patterns": 0.4,
                "stylistic_consistency": 0.3,
            },
            "flagged_sections": [],
            "sentence_analysis": [
                {
                    "text": "Hello world.",
                    "is_ai": False,
                    "confidence": 0.8,
                    "reason": "Looks human.",
                    "features": {},
                }
            ],
            "structured_blocks": [],
            "detailed_analysis": ["Analysis point 1"],
            "model_versions": {
                "roberta-base-openai-detector": "latest",
                "fakespot-ai/roberta-base-ai-text-detection-v1": "latest",
            },
            "analysis_timestamp": datetime.now(UTC).isoformat(),
        }
        base.update(overrides)
        return base

    def test_valid_response_parses(self):
        data = self._make_valid_response()
        resp = AIDetectionResponse(**data)
        assert resp.document_id == "abc-123"
        assert resp.detection_result == DetectionResult.HUMAN
        assert resp.confidence_score == 0.85

    def test_model_versions_included(self):
        data = self._make_valid_response()
        resp = AIDetectionResponse(**data)
        assert "roberta-base-openai-detector" in resp.model_versions
        assert "fakespot-ai/roberta-base-ai-text-detection-v1" in resp.model_versions

    def test_model_versions_default_empty(self):
        data = self._make_valid_response()
        del data["model_versions"]
        resp = AIDetectionResponse(**data)
        assert resp.model_versions == {}

    def test_invalid_confidence_rejected(self):
        with pytest.raises(Exception):
            AIDetectionResponse(**self._make_valid_response(confidence_score=1.5))

    def test_invalid_detection_result_rejected(self):
        with pytest.raises(Exception):
            AIDetectionResponse(**self._make_valid_response(detection_result="invalid"))

    def test_all_detection_results_valid(self):
        for result in ["human", "ai_generated", "mixed"]:
            data = self._make_valid_response(detection_result=result)
            resp = AIDetectionResponse(**data)
            assert resp.detection_result.value == result


class TestATSScoringResponseContract:
    """Validate ATSScoringResponse schema contract."""

    def _make_valid_response(self, **overrides) -> dict:
        base = {
            "document_id": "doc-456",
            "job_id": "job-789",
            "overall_score": 75.5,
            "keyword_match_score": 80.0,
            "semantic_similarity_score": 70.0,
            "format_score": 76.5,
            "skill_matches": [
                {"skill": "Python", "matched": True, "relevance": 0.95},
                {"skill": "Kubernetes", "matched": False, "relevance": 0.7},
            ],
            "gap_analysis": {
                "missing_required_skills": ["Kubernetes"],
                "missing_preferred_skills": ["Terraform"],
                "recommendations": ["Add Kubernetes experience to resume."],
            },
            "analysis_timestamp": datetime.now(UTC).isoformat(),
        }
        base.update(overrides)
        return base

    def test_valid_response_parses(self):
        data = self._make_valid_response()
        resp = ATSScoringResponse(**data)
        assert resp.overall_score == 75.5
        assert len(resp.skill_matches) == 2

    def test_score_range_validated(self):
        with pytest.raises(Exception):
            ATSScoringResponse(**self._make_valid_response(overall_score=101))

    def test_skill_relevance_range(self):
        with pytest.raises(Exception):
            ATSScoringResponse(
                **self._make_valid_response(
                    skill_matches=[{"skill": "X", "matched": True, "relevance": 1.5}]
                )
            )


class TestLinguisticFeaturesContract:
    """Validate LinguisticFeatures schema bounds."""

    def test_valid_features(self):
        feat = LinguisticFeatures(
            sentence_complexity=0.5,
            vocabulary_diversity=0.6,
            coherence_score=0.7,
            transition_patterns=0.8,
            stylistic_consistency=0.9,
        )
        assert feat.sentence_complexity == 0.5

    def test_out_of_range_rejected(self):
        with pytest.raises(Exception):
            LinguisticFeatures(
                sentence_complexity=1.5,
                vocabulary_diversity=0.5,
                coherence_score=0.5,
                transition_patterns=0.5,
                stylistic_consistency=0.5,
            )


class TestHealthCheckResponseContract:
    """Validate HealthCheckResponse schema."""

    def test_valid_healthy(self):
        resp = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now(UTC),
            services={"database": True, "redis": True},
        )
        assert resp.status == "healthy"

    def test_valid_degraded(self):
        resp = HealthCheckResponse(
            status="degraded",
            version="1.0.0",
            timestamp=datetime.now(UTC),
            services={"database": True, "redis": False},
        )
        assert resp.status == "degraded"

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            HealthCheckResponse(
                status="broken",
                version="1.0.0",
                timestamp=datetime.now(UTC),
                services={},
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
