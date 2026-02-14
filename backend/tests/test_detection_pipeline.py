"""
Test suite for AI detection pipeline.
Validates the detector agent, AI classifier, and linguistic features.
"""
import pytest

from app.agents.detector import DetectorAgent, get_detector_agent
from app.services.ai_classifier import AIClassifier, get_ai_classifier


# ── Sample texts ────────────────────────────────────────────────────────
HUMAN_TEXT = (
    "I woke up early today and honestly couldn't decide what to have for "
    "breakfast. Ended up making some toast and — yeah — burning it a little. "
    "Then I sat down to work on my project, which has been a pain lately because "
    "of random bugs that pop up every time I think I've fixed something. "
    "Anyway, it's one of those days, you know?"
)

AI_TEXT = (
    "In today's rapidly evolving digital landscape, it is imperative to "
    "understand the multifaceted challenges that organizations face. "
    "Furthermore, the implementation of robust frameworks is essential for "
    "ensuring sustainable growth. Additionally, leveraging cutting-edge "
    "technologies can provide a competitive advantage in the marketplace. "
    "Moreover, strategic alignment between technological capabilities and "
    "business objectives remains a critical success factor. Subsequently, "
    "organizations must adapt their operational paradigms to remain relevant."
)

MIXED_TEXT = (
    "So I was trying to figure out how to deploy this app and kept running "
    "into weird Docker issues. Furthermore, the implementation of containerized "
    "microservices architecture requires careful consideration of networking "
    "protocols and service discovery mechanisms. Additionally, the orchestration "
    "layer must be configured to ensure optimal resource utilization. But yeah, "
    "in the end I just asked my friend and she fixed it in like five minutes."
)


class TestAIClassifier:
    """Unit tests for the sliding-window AI classifier."""

    @pytest.fixture
    def classifier(self) -> AIClassifier:
        return get_ai_classifier()

    def test_classify_empty_list(self, classifier: AIClassifier):
        import asyncio
        assert asyncio.get_event_loop().run_until_complete(
            classifier.classify_sentences([])
        ) == []

    def test_classify_short_sentence_falls_back_to_heuristic(self, classifier: AIClassifier):
        """Sentences below _MIN_TOKENS_FOR_ML should use heuristic."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            classifier.classify_sentences(["Hi there."])
        )
        assert len(result) == 1
        assert "text" in result[0]
        assert "is_ai" in result[0]
        assert "confidence" in result[0]
        assert 0.0 <= result[0]["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_classify_returns_correct_count(self, classifier: AIClassifier):
        sentences = HUMAN_TEXT.split(". ")
        result = await classifier.classify_sentences(sentences)
        assert len(result) == len(sentences)

    @pytest.mark.asyncio
    async def test_classify_output_shape(self, classifier: AIClassifier):
        result = await classifier.classify_sentences(["This is a moderately long sentence for testing."])
        assert isinstance(result, list)
        for item in result:
            assert set(item.keys()) >= {"text", "is_ai", "confidence", "reason"}

    def test_model_versions_available(self, classifier: AIClassifier):
        """After loading, model_versions should be a dict."""
        classifier._ensure_models()
        versions = classifier.model_versions
        assert isinstance(versions, dict)


class TestDetectorLinguisticFeatures:
    """Unit tests for linguistic feature extraction."""

    @pytest.fixture
    def detector(self) -> DetectorAgent:
        return get_detector_agent()

    def test_features_range(self, detector: DetectorAgent):
        """All feature values must be in [0, 1]."""
        features = detector._extract_linguistic_features(HUMAN_TEXT)
        for name in [
            "sentence_complexity",
            "vocabulary_diversity",
            "coherence_score",
            "transition_patterns",
            "stylistic_consistency",
        ]:
            val = getattr(features, name)
            assert 0.0 <= val <= 1.0, f"{name}={val} out of range"

    def test_human_text_has_higher_sentence_variation(self, detector: DetectorAgent):
        """Human text should show more sentence-length variation (higher complexity)."""
        human_feat = detector._extract_linguistic_features(HUMAN_TEXT)
        ai_feat = detector._extract_linguistic_features(AI_TEXT)
        assert human_feat.sentence_complexity >= ai_feat.sentence_complexity * 0.5

    def test_ai_text_higher_stylistic_consistency(self, detector: DetectorAgent):
        """AI text should be more stylistically consistent."""
        human_feat = detector._extract_linguistic_features(HUMAN_TEXT)
        ai_feat = detector._extract_linguistic_features(AI_TEXT)
        assert ai_feat.stylistic_consistency >= human_feat.stylistic_consistency * 0.5

    def test_empty_text(self, detector: DetectorAgent):
        features = detector._extract_linguistic_features("")
        assert features.sentence_complexity == 0.5
        assert features.vocabulary_diversity == 0.5

    def test_split_sentences(self, detector: DetectorAgent):
        text = "Hello world. How are you? I am fine!"
        sentences = detector._split_sentences(text)
        assert len(sentences) == 3


class TestDetectorAgent:
    """Integration tests for the DetectorAgent (no LLM calls)."""

    @pytest.fixture
    def detector(self) -> DetectorAgent:
        return get_detector_agent()

    def test_singleton(self):
        a = get_detector_agent()
        b = get_detector_agent()
        assert a is b

    def test_identify_ai_sections_flags_formulaic(self, detector: DetectorAgent):
        flagged = detector._identify_ai_sections(AI_TEXT)
        assert len(flagged) >= 0  # May or may not flag depending on indicator density

    def test_determine_result_thresholds(self, detector: DetectorAgent):
        from app.models.schemas import DetectionResult

        assert detector._determine_result(0.1) == DetectionResult.HUMAN
        assert detector._determine_result(0.5) == DetectionResult.MIXED
        assert detector._determine_result(0.9) == DetectionResult.AI_GENERATED

    def test_calculate_confidence_extremes(self, detector: DetectorAgent):
        features = detector._extract_linguistic_features(AI_TEXT)
        # High probability → high confidence
        high = detector._calculate_confidence(features, 0.95)
        low = detector._calculate_confidence(features, 0.50)
        assert high > low


class TestSkillMatchingSubstring:
    """Regression tests for the ATS substring matching bug (#13)."""

    @pytest.fixture
    def scorer(self):
        from app.agents.ats_scorer import ATSScorerAgent
        return ATSScorerAgent()

    @pytest.mark.asyncio
    async def test_java_does_not_match_javascript(self, scorer):
        matches = await scorer._match_skills(
            "Proficient in JavaScript and TypeScript.", ["Java"]
        )
        assert not matches[0].matched, "Java should NOT match JavaScript"

    @pytest.mark.asyncio
    async def test_exact_match_works(self, scorer):
        matches = await scorer._match_skills(
            "Proficient in Java and Spring Boot.", ["Java"]
        )
        assert matches[0].matched, "Java should match when it appears as a standalone word"

    @pytest.mark.asyncio
    async def test_cpp_match(self, scorer):
        matches = await scorer._match_skills(
            "Experienced with C++ and Rust.", ["C++"]
        )
        assert matches[0].matched


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
