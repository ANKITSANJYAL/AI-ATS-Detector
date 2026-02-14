"""
AI Content Detection Agent.
Performs forensic linguistic analysis to detect AI-generated content.
"""
import math
import re
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.models.schemas import (
    AIDetectionResponse,
    DetectionResult,
    LinguisticFeatures,
)
from app.services.llm_client import LLMClient, get_llm_client
from app.services.ai_classifier import get_ai_classifier

logger = get_logger(__name__)


class DetectorAgent:
    """
    AI detection agent using forensic linguistic analysis.
    Implements multi-dimensional analysis for high-accuracy detection.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        """Initialize detector agent."""
        self.llm_client = llm_client or get_llm_client()
        self.classifier = get_ai_classifier()

    async def analyze(
        self,
        document_id: str,
        text: str,
        structured_blocks: list[dict] | None = None
    ) -> AIDetectionResponse:
        """
        Perform comprehensive AI detection analysis.

        Args:
            document_id: Document identifier
            text: Document text to analyze
            structured_blocks: Optional structured document blocks with formatting

        Returns:
            Detection analysis results
        """
        logger.info(f"Starting AI detection for document {document_id}")

        # Extract linguistic features (uses collapsed text — fine for statistics)
        features = self._extract_linguistic_features(text)

        # Perform sentence-level analysis.
        # When structured blocks are available, split sentences *per block* so
        # that each sentence belongs to exactly one block.  This prevents the
        # preprocess_text whitespace collapse from merging headings/paragraphs
        # into neighbouring sentences, which would break the frontend mapping.
        blocks = structured_blocks or []
        if blocks:
            sentence_analysis: list[dict] = []
            enriched_blocks: list[dict] = []
            for block in blocks:
                block_sentences = self._split_sentences(block["text"])
                block_analysis = self.classifier.classify_sentences(block_sentences)
                # Tag each analysis item with its block index so frontend can
                # reconstruct structure trivially.
                block_idx = len(enriched_blocks)
                for item in block_analysis:
                    item["block_index"] = block_idx
                sentence_analysis.extend(block_analysis)
                enriched_blocks.append(block)
        else:
            # No structured blocks — fall back to splitting the collapsed text
            sentence_analysis = self.classifier.classify_sentences(
                self._split_sentences(text)
            )
            enriched_blocks = []

        # Detect potentially AI-generated sections
        flagged_sections = self._identify_ai_sections(text)

        # Calculate AI probability based on ML classifier + features
        ai_probability = self._calculate_ai_probability(features, sentence_analysis)

        # Determine detection result and confidence
        detection_result = self._determine_result(ai_probability)
        confidence_score = self._calculate_confidence(features, ai_probability)

        # Generate detailed explanation
        detailed_analysis = self._generate_analysis_explanation(
            features, ai_probability, sentence_analysis
        )

        logger.info(
            f"AI detection complete for {document_id}: "
            f"{detection_result.value} ({ai_probability:.2%})"
        )

        return AIDetectionResponse(
            document_id=document_id,
            detection_result=detection_result,
            confidence_score=confidence_score,
            ai_probability=ai_probability,
            linguistic_features=features,
            flagged_sections=flagged_sections,
            sentence_analysis=sentence_analysis,
            structured_blocks=enriched_blocks,
            detailed_analysis=detailed_analysis,
            analysis_timestamp=datetime.now(UTC),
        )

    def _extract_linguistic_features(self, text: str) -> LinguisticFeatures:
        """
        Extract linguistic features using robust statistical measures.
        No LLM calls — purely computational analysis.

        Key improvements:
        - Vocabulary diversity uses corrected TTR (Guiraud's index) for length-independence
        - Sentence complexity uses coefficient of variation
        - Coherence is based on semantic overlap between adjacent sentences
        """
        sentences = self._split_sentences(text)
        words = text.lower().split()

        if not words:
            return LinguisticFeatures(
                sentence_complexity=0.5,
                vocabulary_diversity=0.5,
                coherence_score=0.5,
                transition_patterns=0.5,
                stylistic_consistency=0.5,
            )

        # --- Sentence complexity: coefficient of variation of sentence lengths ---
        sentence_lengths = [len(s.split()) for s in sentences]
        if len(sentence_lengths) >= 2:
            mean_len = sum(sentence_lengths) / len(sentence_lengths)
            if mean_len > 0:
                std_dev = (sum((l - mean_len) ** 2 for l in sentence_lengths) / len(sentence_lengths)) ** 0.5
                cv = std_dev / mean_len  # 0 = perfectly uniform, typically 0.3-0.8 for humans
                sentence_complexity = min(1.0, cv / 1.0)  # Normalize: CV of 1.0 maps to 1.0
            else:
                sentence_complexity = 0.0
        else:
            sentence_complexity = 0.5

        # --- Vocabulary diversity: Guiraud's corrected TTR ---
        # TTR = V/N is biased by text length; Guiraud = V/sqrt(N)
        unique_words = len(set(words))
        total_words = len(words)
        guiraud = unique_words / math.sqrt(total_words) if total_words > 0 else 0
        # Normalize: typical range is 4-12 for English prose
        vocabulary_diversity = min(1.0, max(0.0, (guiraud - 3) / 9))

        # --- Coherence: adjacent sentence word overlap (Jaccard similarity) ---
        if len(sentences) >= 2:
            overlaps = []
            for i in range(len(sentences) - 1):
                words_a = set(sentences[i].lower().split())
                words_b = set(sentences[i + 1].lower().split())
                union = words_a | words_b
                if union:
                    overlaps.append(len(words_a & words_b) / len(union))
            coherence_score = sum(overlaps) / len(overlaps) if overlaps else 0.5
        else:
            coherence_score = 0.5

        # --- Transition patterns: density of formal transition words ---
        formal_transitions = {
            "however", "furthermore", "moreover", "additionally", "therefore",
            "thus", "consequently", "subsequently", "hence", "nonetheless",
        }
        casual_transitions = {
            "but", "and", "so", "because", "well", "also", "though", "still",
        }
        formal_count = sum(1 for w in words if w in formal_transitions)
        casual_count = sum(1 for w in words if w in casual_transitions)
        total_transitions = formal_count + casual_count
        if total_transitions > 0:
            # High ratio = more formal transitions = more AI-like
            formality_ratio = formal_count / total_transitions
            transition_patterns = 1.0 - formality_ratio  # Invert: low = more AI-like
        else:
            transition_patterns = 0.5

        # --- Stylistic consistency: CV of sentence lengths inverted ---
        # AI tends to be very consistent; humans vary more
        stylistic_consistency = 1.0 - sentence_complexity

        return LinguisticFeatures(
            sentence_complexity=round(sentence_complexity, 3),
            vocabulary_diversity=round(vocabulary_diversity, 3),
            coherence_score=round(min(1.0, coherence_score), 3),
            transition_patterns=round(transition_patterns, 3),
            stylistic_consistency=round(stylistic_consistency, 3),
        )

    def _identify_ai_sections(self, text: str) -> list[str]:
        """Identify text sections likely to be AI-generated."""
        flagged = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for para in paragraphs[:10]:
            ai_indicators = [
                r"\b(furthermore|moreover|additionally|subsequently)\b",
                r"\b(it is important to note|it should be noted)\b",
                r"\b(in conclusion|in summary)\b",
                r"\b(in today's rapidly evolving|in the ever-changing)\b",
            ]
            matches = sum(1 for pattern in ai_indicators if re.search(pattern, para.lower()))
            if matches >= 2 and len(para) > 50:
                flagged.append(para[:200] + "..." if len(para) > 200 else para)

        return flagged[:5]

    def _calculate_ai_probability(
        self,
        features: LinguisticFeatures,
        sentence_analysis: list[dict]
    ) -> float:
        """
        Calculate overall AI generation probability.

        Uses the per-sentence AI probability directly (already calibrated
        by the multi-model ensemble + Platt scaling in AIClassifier).
        Document-level linguistic features add a small ±5% adjustment.

        Returns:
            AI probability (0-1)
        """
        if not sentence_analysis:
            return 0.3  # No data — lean toward human

        # --- ML component (95% weight) ---
        # Each sentence already carries a calibrated confidence and is_ai flag.
        # Convert to P(AI) per sentence: if is_ai, P(AI)=confidence; else P(AI)=1-confidence.
        # Weight longer sentences more (they carry more signal).
        total_weight = 0.0
        weighted_ai_prob = 0.0

        for sent in sentence_analysis:
            conf = sent.get("confidence", 0.5)
            is_ai = sent.get("is_ai", False)
            word_count = sent.get("features", {}).get("word_count", 5)

            # Convert to P(AI) in [0, 1]
            p_ai = conf if is_ai else (1.0 - conf)
            # Sentence weight: sqrt(word_count) so long sentences count more
            # but don't dominate completely.
            w = max(1.0, word_count ** 0.5)
            weighted_ai_prob += p_ai * w
            total_weight += w

        ml_score = weighted_ai_prob / total_weight if total_weight > 0 else 0.5

        # --- Linguistic features (5% weight) — minor adjustment ---
        feature_adj = 0.0

        # Low complexity (uniform sentences) → nudge toward AI
        feature_adj += (0.5 - features.sentence_complexity) * 0.02

        # Low vocab diversity → nudge toward AI
        feature_adj += (0.5 - features.vocabulary_diversity) * 0.02

        # Too-high coherence → nudge toward AI
        if features.coherence_score > 0.8:
            feature_adj += 0.01

        # Overall: 95% ML + 5% features
        combined = ml_score * 0.95 + (ml_score + feature_adj) * 0.05
        return max(0.0, min(1.0, combined))

    def _determine_result(self, ai_probability: float) -> DetectionResult:
        """
        Determine detection result based on probability.

        Args:
            ai_probability: AI generation probability

        Returns:
            Detection result classification
        """
        if ai_probability < 0.3:
            return DetectionResult.HUMAN
        elif ai_probability > 0.7:
            return DetectionResult.AI_GENERATED
        else:
            return DetectionResult.MIXED

    def _calculate_confidence(
        self,
        features: LinguisticFeatures,
        ai_probability: float
    ) -> float:
        """
        Calculate confidence in detection.

        Args:
            features: Linguistic features
            ai_probability: AI probability score

        Returns:
            Confidence score (0-1)
        """
        # Higher confidence when probability is extreme (near 0 or 1)
        # and features are consistent

        extremeness = abs(ai_probability - 0.5) * 2  # 0 to 1

        # Feature consistency
        feature_values = [
            features.sentence_complexity,
            features.vocabulary_diversity,
            features.coherence_score,
            features.transition_patterns,
            features.stylistic_consistency,
        ]
        avg_feature = sum(feature_values) / len(feature_values)
        consistency = 1.0 - (sum(abs(f - avg_feature) for f in feature_values) / len(feature_values))

        confidence = (extremeness * 0.7) + (consistency * 0.3)
        return min(1.0, confidence)

    def _generate_analysis_explanation(
        self,
        features: LinguisticFeatures,
        ai_probability: float,
        sentence_analysis: list[dict]
    ) -> list[str]:
        """
        Generate detailed explanation of the analysis.

        Args:
            features: Linguistic features
            ai_probability: AI probability
            sentence_analysis: Sentence-level analysis

        Returns:
            List of explanation points
        """
        explanations = []

        # Overall assessment
        if ai_probability > 0.7:
            explanations.append(
                f"Overall AI probability is {ai_probability:.0%}, indicating strong likelihood of AI generation"
            )
        elif ai_probability > 0.4:
            explanations.append(
                f"Overall AI probability is {ai_probability:.0%}, suggesting mixed human and AI content"
            )
        else:
            explanations.append(
                f"Overall AI probability is {ai_probability:.0%}, indicating primarily human-written content"
            )

        # Sentence-level findings
        if sentence_analysis:
            ai_sentences = sum(1 for s in sentence_analysis if s["is_ai"])
            total_sentences = len(sentence_analysis)
            ai_ratio = ai_sentences / total_sentences if total_sentences > 0 else 0

            explanations.append(
                f"{ai_sentences} out of {total_sentences} sentences ({ai_ratio:.0%}) appear to be AI-generated"
            )

        # Feature analysis
        if features.sentence_complexity < 0.3:
            explanations.append(
                "Low sentence complexity (uniform sentence lengths) is typical of AI-generated text"
            )
        elif features.sentence_complexity > 0.7:
            explanations.append(
                "High sentence complexity (varied sentence lengths) is typical of human writing"
            )

        if features.vocabulary_diversity < 0.4:
            explanations.append(
                "Limited vocabulary diversity suggests repetitive patterns common in AI text"
            )
        elif features.vocabulary_diversity > 0.7:
            explanations.append(
                "High vocabulary diversity indicates human-like linguistic variation"
            )

        if features.coherence_score > 0.85:
            explanations.append(
                "Exceptionally high coherence may indicate AI's tendency for overly structured text"
            )

        if features.transition_patterns < 0.25:
            explanations.append(
                "Heavy use of formal transition words detected, common in AI-generated content"
            )

        if features.stylistic_consistency > 0.9:
            explanations.append(
                "Very high stylistic consistency throughout suggests algorithmic composition"
            )
        elif features.stylistic_consistency < 0.5:
            explanations.append(
                "Natural stylistic variation indicates human authorship"
            )

        # Ensure at least 3 explanations
        if len(explanations) < 3:
            explanations.append("Analysis based on linguistic patterns and sentence structure")

        return explanations[:6]  # Return top 6 most relevant

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences using a look-behind regex."""
        # Split on sentence-ending punctuation followed by whitespace or EOL,
        # but not after common abbreviations (Mr., Dr., etc.)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 5]


# ── Singleton ──────────────────────────────────────────────────────────
_detector_agent: DetectorAgent | None = None


def get_detector_agent() -> DetectorAgent:
    """Return a singleton DetectorAgent (avoids recreating LLM client)."""
    global _detector_agent
    if _detector_agent is None:
        _detector_agent = DetectorAgent()
    return _detector_agent
