"""
Unit tests for AIClassifier with mocked transformer models.
Validates ensemble logic, log-odds pooling, calibration, and window aggregation
without requiring real model weights (fast, no GPU needed).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_classifier import AIClassifier

# ── Helpers ────────────────────────────────────────────────────────────

def _make_mock_model(ai_prob: float):
    """Create a mock model entry that always returns a fixed P(AI)."""

    mock_config = MagicMock()
    mock_config.id2label = {0: "Human", 1: "AI"}
    mock_config._name_or_path = "mock-model"

    mock_model = MagicMock()
    mock_model.config = mock_config
    mock_model.eval = MagicMock()

    # Build a mock that simulates torch.softmax output
    mock_probs_row = MagicMock()
    mock_probs_row.__getitem__ = lambda self, idx: MagicMock(item=lambda: ai_prob if idx == 1 else 1 - ai_prob)
    mock_probs = MagicMock()
    mock_probs.__getitem__ = lambda self, idx: mock_probs_row

    mock_logits = MagicMock()
    mock_outputs = MagicMock()
    mock_outputs.logits = mock_logits

    mock_model.__call__ = lambda self, **kwargs: mock_outputs

    mock_tokenizer = MagicMock()
    mock_tokenizer.__call__ = lambda self, *args, **kwargs: {"input_ids": MagicMock()}

    return {
        "model": mock_model,
        "tokenizer": mock_tokenizer,
        "name": "mock-model",
        "weight": 1.0,
    }


class TestCalibration:
    """Tests for calibration (identity transform with optional intercept)."""

    def test_calibrate_midpoint(self):
        """p=0.5 should stay at 0.5 with identity calibration."""
        clf = AIClassifier()
        cal = clf._calibrate(0.5)
        # logit(0.5) = 0 → cal_logit = 1.0*0 + 0.0 = 0 → sigmoid(0) = 0.5
        assert 0.49 < cal < 0.51

    def test_calibrate_high_preserved(self):
        """p=0.99 should stay near 0.99 with identity calibration."""
        clf = AIClassifier()
        raw = 0.99
        cal = clf._calibrate(raw)
        assert abs(cal - raw) < 0.01, "Identity calibration should preserve the signal"

    def test_calibrate_low_preserved(self):
        """p=0.01 should stay near 0.01 with identity calibration."""
        clf = AIClassifier()
        raw = 0.01
        cal = clf._calibrate(raw)
        assert abs(cal - raw) < 0.01, "Identity calibration should preserve the signal"

    def test_calibrate_monotonic(self):
        """Calibrated probabilities should be monotonically increasing."""
        clf = AIClassifier()
        prev = 0.0
        for p in [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]:
            cal = clf._calibrate(p)
            assert cal >= prev, f"Monotonicity violated at p={p}"
            prev = cal


class TestLogOddsPooling:
    """Tests for log-odds ensemble pooling."""

    def test_single_model_passthrough(self):
        """With one model, pooled result should equal that model's calibrated output."""
        clf = AIClassifier()
        clf._loaded = True
        clf._models = [_make_mock_model(0.8)]

        # Patch torch.softmax to return our mock probs
        with patch("app.services.ai_classifier.AIClassifier._infer_one", return_value=0.8):
            result = clf._ensemble_predict_sync("test text")

        # Should be calibrate(0.8)
        expected = clf._calibrate(0.8)
        assert abs(result - expected) < 0.01

    def test_two_models_agreement(self):
        """When both models agree, result should be near that agreement."""
        clf = AIClassifier()
        clf._loaded = True
        clf._models = [
            {**_make_mock_model(0.9), "weight": 0.5},
            {**_make_mock_model(0.85), "weight": 0.5},
        ]

        with patch("app.services.ai_classifier.AIClassifier._infer_one", side_effect=[0.9, 0.85]):
            result = clf._ensemble_predict_sync("test text")

        assert result > 0.5, "Both models say AI, ensemble should agree"

    def test_two_models_disagreement(self):
        """When models disagree, result should be pulled toward 0.5."""
        clf = AIClassifier()
        clf._loaded = True
        clf._models = [
            {**_make_mock_model(0.9), "weight": 0.5},
            {**_make_mock_model(0.1), "weight": 0.5},
        ]

        with patch("app.services.ai_classifier.AIClassifier._infer_one", side_effect=[0.9, 0.1]):
            result = clf._ensemble_predict_sync("test text")

        # In log-odds space, 0.9 + 0.1 should average near 0.5
        assert 0.3 < result < 0.7, f"Disagreement should pull toward center, got {result}"

    def test_no_models_returns_half(self):
        """With no models loaded, should return 0.5."""
        clf = AIClassifier()
        clf._loaded = True
        clf._models = []
        result = clf._ensemble_predict_sync("test text")
        assert result == 0.5


class TestSentenceFeatures:
    """Tests for linguistic feature computation."""

    def test_empty_text(self):
        feats = AIClassifier._compute_sentence_features("")
        assert feats["word_count"] == 0
        assert feats["avg_word_length"] == 0.0

    def test_personal_voice_detected(self):
        feats = AIClassifier._compute_sentence_features("I think this is my best work.")
        assert feats["personal_voice"] is True

    def test_no_personal_voice(self):
        feats = AIClassifier._compute_sentence_features("The results indicate significant improvement.")
        assert feats["personal_voice"] is False

    def test_contractions_counted(self):
        feats = AIClassifier._compute_sentence_features("I don't think it's going to work.")
        assert feats["contraction_count"] >= 2

    def test_passive_voice_detected(self):
        feats = AIClassifier._compute_sentence_features("The report was written by the team.")
        assert feats["has_passive_voice"] is True

    def test_sentence_length_class(self):
        short = AIClassifier._compute_sentence_features("Hello there.")
        assert short["sentence_length_class"] == "short"

        long_text = " ".join(["word"] * 30)
        long_feats = AIClassifier._compute_sentence_features(long_text)
        assert long_feats["sentence_length_class"] == "long"


class TestFeatureReason:
    """Tests for explanation generation."""

    def test_ai_cliche_detection(self):
        text = "It is important to note that AI is transforming the landscape."
        feats = AIClassifier._compute_sentence_features(text)
        reason = AIClassifier._build_feature_reason(text, True, 0.85, feats)
        assert "AI-typical" in reason

    def test_human_label(self):
        text = "I personally think cats are better than dogs."
        feats = AIClassifier._compute_sentence_features(text)
        reason = AIClassifier._build_feature_reason(text, False, 0.75, feats)
        assert "human-written" in reason

    def test_fallback_when_no_clues(self):
        text = "Medium length sentence with average features."
        feats = AIClassifier._compute_sentence_features(text)
        reason = AIClassifier._build_feature_reason(text, True, 0.55, feats)
        assert "confidence" in reason.lower()


class TestModelVersions:
    """Tests for model version tracking."""

    def test_versions_empty_before_load(self):
        clf = AIClassifier()
        assert clf.model_versions == {}

    def test_versions_populated_after_mock_load(self):
        clf = AIClassifier()
        clf._loaded = True
        clf._model_versions = {"model-a": "v1", "model-b": "v2"}
        assert len(clf.model_versions) == 2
        assert clf.model_versions["model-a"] == "v1"


class TestClassifySentencesAsync:
    """Tests for async classify_sentences."""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        clf = AIClassifier()
        result = await clf.classify_sentences([])
        assert result == []

    @pytest.mark.asyncio
    async def test_no_models_returns_default(self):
        clf = AIClassifier()
        clf._loaded = True
        clf._models = []
        result = await clf.classify_sentences(["This is a test sentence."])
        assert len(result) == 1
        assert result[0]["confidence"] == 0.5

    @pytest.mark.asyncio
    async def test_output_shape(self):
        clf = AIClassifier()
        clf._loaded = True
        clf._models = [_make_mock_model(0.7)]

        with patch.object(clf, "_ensemble_predict", new_callable=AsyncMock, return_value=0.7):
            result = await clf.classify_sentences(["This is a moderately long test sentence for validation."])
            assert len(result) == 1
            assert set(result[0].keys()) >= {"text", "is_ai", "confidence", "reason", "features"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
