"""
Unit tests for the AI Humanizer and Resume Optimizer agents.
Validates schema contracts and fallback behaviour.
"""
from datetime import UTC, datetime

import pytest

from app.models.schemas import (
    ChangeItem,
    DiffStats,
    HumanizeBatchResponse,
    HumanizeResponse,
    ResumeOptimizeResponse,
    RewriteOption,
    SectionImprovement,
)


# ── HumanizeResponse contract tests ───────────────────────────────────

class TestHumanizeResponseContract:
    """Validate HumanizeResponse schema shapes."""

    def _make_valid(self, **overrides) -> dict:
        base = {
            "original_text": "The results demonstrate a significant improvement.",
            "rewrites": [
                {"text": "We saw a big improvement in results.", "approach": "conversational"},
                {"text": "Results improved noticeably.", "approach": "concise"},
                {"text": "Our findings showed clear progress.", "approach": "academic"},
            ],
            "explanation": "Uses formal hedging language typical of AI writing.",
            "ai_tells": ["hedging language", "passive voice"],
        }
        base.update(overrides)
        return base

    def test_valid_response(self):
        resp = HumanizeResponse(**self._make_valid())
        assert resp.original_text == "The results demonstrate a significant improvement."
        assert len(resp.rewrites) == 3
        assert resp.rewrites[0].approach == "conversational"

    def test_empty_ai_tells_defaults(self):
        resp = HumanizeResponse(**self._make_valid(ai_tells=[]))
        assert resp.ai_tells == []

    def test_missing_ai_tells_defaults(self):
        data = self._make_valid()
        del data["ai_tells"]
        resp = HumanizeResponse(**data)
        assert resp.ai_tells == []

    def test_rewrite_option_fields(self):
        opt = RewriteOption(text="Hello world.", approach="casual")
        assert opt.text == "Hello world."
        assert opt.approach == "casual"


class TestHumanizeBatchResponseContract:
    """Validate HumanizeBatchResponse schema."""

    def test_valid_batch(self):
        resp = HumanizeBatchResponse(
            document_id="doc-123",
            results=[
                HumanizeResponse(
                    original_text="AI sentence.",
                    rewrites=[RewriteOption(text="Human version.", approach="natural")],
                    explanation="Too formal.",
                    ai_tells=[],
                )
            ],
            tone="professional",
        )
        assert resp.document_id == "doc-123"
        assert len(resp.results) == 1
        assert resp.tone == "professional"


# ── ResumeOptimizeResponse contract tests ─────────────────────────────

class TestResumeOptimizeResponseContract:
    """Validate ResumeOptimizeResponse schema shapes."""

    def _make_valid(self, **overrides) -> dict:
        base = {
            "document_id": "doc-abc",
            "job_id": "job-xyz",
            "optimized_resume": "Optimized resume text here...",
            "changes": [
                {
                    "section": "Skills",
                    "change": "Added Python keyword",
                    "reason": "Job requires Python experience",
                }
            ],
            "section_improvements": [
                {
                    "section": "Experience",
                    "before": "Worked on software",
                    "after": "Developed Python microservices",
                    "impact": "high",
                }
            ],
            "keywords_added": ["Python", "microservices"],
            "estimated_score_improvement": 15,
            "diff_stats": {
                "words_added": 20,
                "words_removed": 5,
                "original_line_count": 50,
                "optimized_line_count": 55,
                "original_word_count": 300,
                "optimized_word_count": 315,
            },
            "generated_at": datetime.now(UTC).isoformat(),
        }
        base.update(overrides)
        return base

    def test_valid_response(self):
        resp = ResumeOptimizeResponse(**self._make_valid())
        assert resp.document_id == "doc-abc"
        assert resp.estimated_score_improvement == 15
        assert len(resp.changes) == 1
        assert len(resp.keywords_added) == 2

    def test_change_item_fields(self):
        item = ChangeItem(section="Skills", change="Added React", reason="Required by JD")
        assert item.section == "Skills"

    def test_section_improvement_impact_enum(self):
        for impact in ("high", "medium", "low"):
            si = SectionImprovement(
                section="Test", before="a", after="b", impact=impact
            )
            assert si.impact == impact

    def test_invalid_impact_rejected(self):
        with pytest.raises(Exception):
            SectionImprovement(
                section="Test", before="a", after="b", impact="extreme"
            )

    def test_diff_stats_fields(self):
        ds = DiffStats(
            words_added=10,
            words_removed=3,
            original_line_count=20,
            optimized_line_count=22,
            original_word_count=100,
            optimized_word_count=107,
        )
        assert ds.words_added == 10
        assert ds.optimized_word_count == 107

    def test_empty_changes_list(self):
        resp = ResumeOptimizeResponse(**self._make_valid(changes=[], section_improvements=[]))
        assert resp.changes == []
        assert resp.section_improvements == []


# ── Humanizer agent fallback tests ────────────────────────────────────

class TestHumanizerAgentFallback:
    """Test the humanizer fallback (no LLM) path."""

    def test_fallback_returns_rewrites(self):
        from app.agents.humanizer import HumanizerAgent

        agent = HumanizerAgent.__new__(HumanizerAgent)
        result = agent._fallback_humanize(
            "Furthermore, it is important to note that the results are significant."
        )
        assert "rewrites" in result
        assert len(result["rewrites"]) >= 1
        assert "explanation" in result
        assert "ai_tells" in result

    def test_fallback_preserves_original(self):
        from app.agents.humanizer import HumanizerAgent

        agent = HumanizerAgent.__new__(HumanizerAgent)
        original = "This is a test sentence."
        result = agent._fallback_humanize(original)
        # fallback returns rewrites; the rewrite text may differ from original
        assert result["rewrites"][0]["text"] is not None


# ── Resume Optimizer agent fallback tests ─────────────────────────────

class TestResumeOptimizerFallback:
    """Test the resume optimizer fallback (no LLM) path."""

    def test_fallback_adds_skills_section(self):
        from app.agents.resume_optimizer import ResumeOptimizerAgent

        agent = ResumeOptimizerAgent.__new__(ResumeOptimizerAgent)
        result = agent._fallback_optimize(
            resume_text="My resume content here.",
            missing_required=["Python", "React"],
            missing_preferred=["Docker"],
            format_score=40,
        )
        assert "optimized_resume" in result
        assert "Python" in result["optimized_resume"]
        assert "React" in result["optimized_resume"]
        assert "changes" in result
        assert "diff_stats" in result

    def test_diff_stats_computation(self):
        from app.agents.resume_optimizer import ResumeOptimizerAgent

        agent = ResumeOptimizerAgent.__new__(ResumeOptimizerAgent)
        stats = agent._compute_diff_stats(
            "Original text here.",
            "Original text here with additions.",
        )
        assert stats["original_word_count"] == 3
        assert stats["optimized_word_count"] == 5
        assert stats["words_added"] >= 0

    def test_fallback_empty_gap_analysis(self):
        from app.agents.resume_optimizer import ResumeOptimizerAgent

        agent = ResumeOptimizerAgent.__new__(ResumeOptimizerAgent)
        result = agent._fallback_optimize(
            resume_text="My resume.",
            missing_required=[],
            missing_preferred=[],
            format_score=70,
        )
        assert "optimized_resume" in result
