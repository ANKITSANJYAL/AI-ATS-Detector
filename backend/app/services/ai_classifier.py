"""
AI Content Classifier Service.
Uses a multi-model ensemble for AI-generated text detection.

Architecture:
- Primary model: roberta-base-openai-detector (trained on GPT-2 output)
- Secondary model: Hello-SimpleAI/chatgpt-detector-roberta (trained on ChatGPT output)
- Ensemble: Weighted average of both models' AI probabilities.
  When models disagree the confidence is automatically lowered.
- Sliding-window inference (256-token windows, 128-stride) for long texts
- Per-sentence linguistic feature computation for explainable reasons
- Temperature-scaled Platt calibration to fix overconfident predictions
"""
import math
import re
from functools import lru_cache

from app.core.logging import get_logger

logger = get_logger(__name__)

# Sliding window parameters
_WINDOW_SIZE_TOKENS = 256
_WINDOW_STRIDE_TOKENS = 128

# Platt calibration parameters (sigmoid correction)
# The raw models are overconfident (trained on GPT-2/ChatGPT, tested on GPT-4/Claude).
# P_calibrated = 1 / (1 + exp(-(a*logit + b)))
# a < 1 compresses predictions toward 0.5; b < 0 shifts slightly toward human.
_PLATT_A = 0.60   # slope — compresses extreme predictions
_PLATT_B = -0.05  # intercept — slight bias toward human


class AIClassifier:
    """
    Multi-model AI content classifier with ensemble inference.

    Key design decisions:
    - Two models are loaded and run independently.  Their raw AI
      probabilities are weighted-averaged.  When they disagree the
      average moves toward 0.5, naturally lowering confidence.
    - Platt (sigmoid) calibration is applied AFTER ensembling so the
      final probability is not overconfident.
    - Per-sentence linguistic features are computed and returned
      alongside the prediction for explainable tooltips.
    """

    def __init__(self):
        self._models: list[dict] = []  # [{model, tokenizer, name, weight}]
        self._loaded = False

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _ensure_models(self):
        """Load both models lazily on first classification call."""
        if self._loaded:
            return
        self._loaded = True

        model_specs = [
            ("roberta-base-openai-detector", 0.35),
            ("Hello-SimpleAI/chatgpt-detector-roberta", 0.65),
        ]

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            torch.set_grad_enabled(False)

            for name, weight in model_specs:
                try:
                    logger.info(f"Loading AI detection model: {name}")
                    tok = AutoTokenizer.from_pretrained(name)
                    mdl = AutoModelForSequenceClassification.from_pretrained(name)
                    mdl.eval()
                    self._models.append({
                        "model": mdl,
                        "tokenizer": tok,
                        "name": name,
                        "weight": weight,
                    })
                    logger.info(f"Loaded model: {name}")
                except Exception as e:
                    logger.warning(f"Could not load model {name}: {e}")

            if not self._models:
                logger.error("CRITICAL: No AI detection models loaded")

        except ImportError as e:
            logger.error(f"transformers/torch not installed: {e}")

    # ------------------------------------------------------------------
    # Platt calibration
    # ------------------------------------------------------------------

    @staticmethod
    def _calibrate(raw_ai_prob: float) -> float:
        """
        Apply Platt sigmoid calibration to compress overconfident scores.
        Maps raw ensemble probability -> calibrated probability.
        """
        p = max(1e-6, min(1 - 1e-6, raw_ai_prob))
        logit = math.log(p / (1 - p))
        cal_logit = _PLATT_A * logit + _PLATT_B
        return 1.0 / (1.0 + math.exp(-cal_logit))

    # ------------------------------------------------------------------
    # Single-model inference
    # ------------------------------------------------------------------

    def _infer_one(self, text: str, model_entry: dict) -> float:
        """Run one model on text, return raw P(AI)."""
        import torch

        tok = model_entry["tokenizer"]
        mdl = model_entry["model"]

        inputs = tok(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        outputs = mdl(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)

        # roberta-base-openai-detector: {0: 'Real', 1: 'Fake'}  → index 1 = AI
        # Hello-SimpleAI/chatgpt-detector-roberta: {0: 'Human', 1: 'ChatGPT'} → index 1 = AI
        # Both models: index 1 = AI
        ai_prob = probs[0][1].item()

        return ai_prob

    # ------------------------------------------------------------------
    # Ensemble inference
    # ------------------------------------------------------------------

    def _ensemble_predict(self, text: str) -> float:
        """
        Run all loaded models, return calibrated P(AI).
        If only one model loaded, uses it alone.
        """
        if not self._models:
            return 0.5

        total_weight = 0.0
        weighted_sum = 0.0

        for entry in self._models:
            raw = self._infer_one(text, entry)
            w = entry["weight"]
            weighted_sum += raw * w
            total_weight += w

        raw_ensemble = weighted_sum / total_weight if total_weight > 0 else 0.5
        return self._calibrate(raw_ensemble)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify_text(self, text: str) -> tuple[bool, float, str]:
        """
        Classify a single text block.
        Returns (is_ai, confidence, reason).
        """
        self._ensure_models()
        if not self._models:
            return False, 0.5, "No models available"

        try:
            ai_prob = self._ensemble_predict(text)
            is_ai = ai_prob > 0.5
            confidence = ai_prob if is_ai else (1.0 - ai_prob)

            features = self._compute_sentence_features(text)
            reason = self._build_feature_reason(text, is_ai, confidence, features)
            return is_ai, confidence, reason

        except Exception as e:
            logger.error(f"Classification error: {e}")
            return False, 0.5, "Classification error"

    def classify_sentences(self, sentences: list[str]) -> list[dict]:
        """
        Classify sentences using sliding-window ensemble aggregation.
        Returns list of dicts: text, is_ai, confidence, reason, features.
        """
        if not sentences:
            return []

        self._ensure_models()

        valid = [(i, s) for i, s in enumerate(sentences) if s.strip()]
        if not valid:
            return []

        if not self._models:
            return [
                {"text": s, "is_ai": False, "confidence": 0.5,
                 "reason": "No models available", "features": {}}
                for s in sentences if s.strip()
            ]

        try:
            return self._classify_sentences_windowed(sentences, valid)
        except Exception as e:
            logger.error(f"Windowed classification failed: {e}")
            return [
                {"text": s, "is_ai": False, "confidence": 0.5,
                 "reason": "Classification error", "features": {}}
                for s in sentences if s.strip()
            ]

    # ------------------------------------------------------------------
    # Windowed classification
    # ------------------------------------------------------------------

    def _classify_sentences_windowed(
        self,
        all_sentences: list[str],
        valid: list[tuple[int, str]],
    ) -> list[dict]:
        """Sliding-window ensemble classification mapped back to sentences."""
        token_counts = [len(s.split()) for _, s in valid]
        total_tokens = sum(token_counts)

        # Small text — single-pass ensemble
        if total_tokens <= _WINDOW_SIZE_TOKENS:
            full_text = " ".join(s for _, s in valid)
            ai_prob = self._ensemble_predict(full_text)
            is_ai = ai_prob > 0.5
            conf = ai_prob if is_ai else (1.0 - ai_prob)

            results = []
            for sent in all_sentences:
                if not sent.strip():
                    continue
                feats = self._compute_sentence_features(sent)
                reason = self._build_feature_reason(sent, is_ai, conf, feats)
                results.append({
                    "text": sent,
                    "is_ai": is_ai,
                    "confidence": round(conf, 3),
                    "reason": reason,
                    "features": feats,
                })
            return results

        # Build overlapping windows
        windows: list[list[int]] = []
        current_window: list[int] = []
        current_tokens = 0

        for vi, (_, sent) in enumerate(valid):
            tc = token_counts[vi]
            if current_tokens + tc > _WINDOW_SIZE_TOKENS and current_window:
                windows.append(current_window)
                overlap_tokens = 0
                overlap_start = len(current_window)
                for j in range(len(current_window) - 1, -1, -1):
                    overlap_tokens += token_counts[current_window[j]]
                    if overlap_tokens >= _WINDOW_STRIDE_TOKENS:
                        overlap_start = j
                        break
                current_window = current_window[overlap_start:]
                current_tokens = sum(token_counts[k] for k in current_window)
            current_window.append(vi)
            current_tokens += tc

        if current_window:
            windows.append(current_window)

        # Per-sentence accumulation across windows
        ai_prob_accum = [0.0] * len(valid)
        weight_accum = [0.0] * len(valid)

        for window_indices in windows:
            window_text = " ".join(valid[vi][1] for vi in window_indices)
            ai_prob = self._ensemble_predict(window_text)
            # Certainty weighting: extreme predictions count more
            certainty = abs(ai_prob - 0.5) * 2.0 + 0.1

            for vi in window_indices:
                ai_prob_accum[vi] += ai_prob * certainty
                weight_accum[vi] += certainty

        # Build results
        valid_idx_map = {orig_i: vi for vi, (orig_i, _) in enumerate(valid)}
        results = []

        for i, sent in enumerate(all_sentences):
            if not sent.strip():
                continue

            vi = valid_idx_map.get(i)
            if vi is not None and weight_accum[vi] > 0:
                avg_ai_prob = ai_prob_accum[vi] / weight_accum[vi]
            else:
                avg_ai_prob = 0.5

            is_ai = avg_ai_prob > 0.5
            confidence = avg_ai_prob if is_ai else (1.0 - avg_ai_prob)

            feats = self._compute_sentence_features(sent)
            reason = self._build_feature_reason(sent, is_ai, confidence, feats)

            results.append({
                "text": sent,
                "is_ai": is_ai,
                "confidence": round(confidence, 3),
                "reason": reason,
                "features": feats,
            })

        return results

    # ------------------------------------------------------------------
    # Per-sentence linguistic feature computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_sentence_features(text: str) -> dict:
        """Compute per-sentence linguistic features for the frontend."""
        text_lower = text.lower()
        words = text_lower.split()
        word_count = len(words)

        if word_count == 0:
            return {
                "word_count": 0, "avg_word_length": 0.0,
                "vocabulary_diversity": 0.0, "formality_score": 0.5,
                "has_passive_voice": False, "sentence_length_class": "short",
                "complexity_score": 0.0, "personal_voice": False,
                "contraction_count": 0, "punctuation_variety": 0.0,
            }

        clean_words = [re.sub(r'[^\w]', '', w) for w in words if re.sub(r'[^\w]', '', w)]
        avg_word_length = (
            sum(len(w) for w in clean_words) / len(clean_words) if clean_words else 0.0
        )

        unique = len(set(words))
        vocab_diversity = unique / word_count

        formal_words = {
            "furthermore", "moreover", "additionally", "consequently",
            "subsequently", "hence", "thereby", "nevertheless",
            "nonetheless", "therefore", "thus", "accordingly",
            "henceforth", "notwithstanding", "whereby",
        }
        casual_words = {
            "but", "and", "so", "because", "well", "also", "though",
            "still", "like", "basically", "actually", "honestly",
            "literally", "gonna", "wanna", "kinda", "sorta",
        }
        formal_count = sum(1 for w in words if w.rstrip(",.;:") in formal_words)
        casual_count = sum(1 for w in words if w.rstrip(",.;:") in casual_words)
        total_markers = formal_count + casual_count
        if total_markers > 0:
            formality = formal_count / total_markers
        else:
            formality = min(1.0, max(0.0, (avg_word_length - 3.5) / 4.0))

        has_passive = bool(re.search(
            r"\b(?:is|are|was|were|been|being)\s+\w+(?:ed|en)\b", text_lower
        ))

        if word_count <= 8:
            length_class = "short"
        elif word_count <= 25:
            length_class = "medium"
        else:
            length_class = "long"

        subordinators = {"which", "whom", "whose", "whereas", "although",
                         "because", "since", "while", "unless", "whether",
                         "that", "where", "when", "if"}
        sub_count = sum(1 for w in words if w in subordinators)
        comma_count = text.count(",") + text.count(";") + text.count(":")
        clause_density = (sub_count + comma_count) / max(1, word_count)
        word_len_factor = min(1.0, max(0.0, (avg_word_length - 3.0) / 4.0))
        length_factor = min(1.0, word_count / 40.0)
        complexity = (word_len_factor * 0.3 + clause_density * 3.0 * 0.4 + length_factor * 0.3)
        complexity = min(1.0, max(0.0, complexity))

        personal_voice = bool(re.search(
            r"\b(i|me|my|myself|we|our|ourselves)\b", text_lower
        ))

        contractions = re.findall(r"\b\w+(?:'(?:t|s|m|re|ve|ll|d))\b", text_lower)
        contraction_count = len(contractions)

        punct_types = set()
        for ch in text:
            if ch in ".,;:!?()\"'":
                punct_types.add(ch)
        punctuation_variety = min(1.0, len(punct_types) / 5.0)

        return {
            "word_count": word_count,
            "avg_word_length": round(avg_word_length, 2),
            "vocabulary_diversity": round(vocab_diversity, 3),
            "formality_score": round(formality, 3),
            "has_passive_voice": has_passive,
            "sentence_length_class": length_class,
            "complexity_score": round(complexity, 3),
            "personal_voice": personal_voice,
            "contraction_count": contraction_count,
            "punctuation_variety": round(punctuation_variety, 3),
        }

    # ------------------------------------------------------------------
    # Feature-based explanation generation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_feature_reason(
        text: str, is_ai: bool, confidence: float, features: dict,
    ) -> str:
        """
        Generate a plain-English explanation citing actual computed features.
        No em-dashes, no semicolons, no colons after labels.
        """
        clues: list[str] = []
        word_count = features.get("word_count", 0)
        vocab_div = features.get("vocabulary_diversity", 0.5)
        formality = features.get("formality_score", 0.5)
        complexity = features.get("complexity_score", 0.5)
        has_passive = features.get("has_passive_voice", False)
        personal = features.get("personal_voice", False)
        contraction_count = features.get("contraction_count", 0)
        avg_wl = features.get("avg_word_length", 4.0)
        length_class = features.get("sentence_length_class", "medium")

        text_lower = text.lower()
        cliches = [
            ("it is important to note", "Uses the AI-typical phrase 'it is important to note'"),
            ("it should be noted", "Uses the AI-typical phrase 'it should be noted'"),
            ("it is worth mentioning", "Uses the AI-typical phrase 'it is worth mentioning'"),
            ("in today's rapidly evolving", "Opens with an AI-typical cliche"),
            ("in the ever-changing landscape", "Opens with an AI-typical cliche"),
        ]
        for phrase, label in cliches:
            if phrase in text_lower:
                clues.append(label)

        if formality > 0.7:
            clues.append(f"The tone is very formal ({formality:.0%}), which is common in AI writing")
        elif formality < 0.3 and word_count >= 5:
            clues.append(f"The tone is casual ({formality:.0%}), which suggests a human wrote this")

        if contraction_count > 0:
            clues.append(
                f"Uses {contraction_count} contraction{'s' if contraction_count > 1 else ''} like natural speech"
            )
        elif word_count > 15 and contraction_count == 0:
            clues.append("No contractions in a long sentence, which feels overly formal")

        if personal:
            clues.append("Written in first person, which feels personal and human")
        if has_passive:
            clues.append("Uses passive voice, which AI tends to do more often")

        if complexity > 0.65:
            clues.append(f"Complex sentence structure ({complexity:.0%}) with multiple clauses")
        elif complexity < 0.2 and word_count >= 5:
            clues.append(f"Very simple sentence structure ({complexity:.0%})")

        if vocab_div < 0.55 and word_count >= 6:
            clues.append(f"Low vocabulary diversity ({vocab_div:.0%}), words repeat a lot")

        if avg_wl > 6.0 and word_count >= 5:
            clues.append(f"Uses long, academic words (avg {avg_wl:.1f} chars per word)")

        if length_class == "long":
            clues.append(f"This is a long sentence ({word_count} words), AI often writes these")
        elif length_class == "short" and word_count <= 4:
            clues.append(f"Very short ({word_count} words), not enough context for a strong call")

        label = "AI-generated" if is_ai else "human-written"

        if not clues:
            return (
                f"The model classified this as {label} with {confidence:.0%} confidence. "
                f"This sentence has {word_count} words, "
                f"{vocab_div:.0%} vocabulary diversity, and "
                f"{complexity:.0%} structural complexity."
            )

        explanation = f"Likely {label} ({confidence:.0%} confidence). "
        explanation += ". ".join(clues[:4])
        if not explanation.endswith("."):
            explanation += "."
        return explanation


@lru_cache(maxsize=1)
def get_ai_classifier() -> AIClassifier:
    """Get cached AI classifier instance."""
    return AIClassifier()
