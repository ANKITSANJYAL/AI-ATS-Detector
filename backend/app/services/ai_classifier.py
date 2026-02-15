"""
AI Content Classifier Service.
Uses a multi-model ensemble for AI-generated text detection.

Architecture:
- Model A: roberta-base-openai-detector (trained on GPT-2 output)
- Model B: Hello-SimpleAI/chatgpt-detector-roberta (trained on ChatGPT output)
- Model C: andreas122001/roberta-academic-detector (trained on academic
           machine-generated text — compatible with transformers 4.x)
- Ensemble: Log-odds (additive logit) pooling of individual model probabilities.
  This is theoretically grounded and handles model disagreement better than
  a naive weighted average.
- Sliding-window inference (512-token windows, 256-stride) for long texts
- Per-sentence linguistic feature computation for explainable reasons
- Light calibration to correct systematic bias without crushing signal

Model registry:
  Every model is pinned to a specific HuggingFace name so results are
  reproducible.  The loaded revision is logged at startup and included
  in API responses via model_versions.
"""
import asyncio
import math
import re
from functools import lru_cache

from app.core.logging import get_logger

logger = get_logger(__name__)

# Sliding window parameters — larger windows provide more context
_WINDOW_SIZE_TOKENS = 512
_WINDOW_STRIDE_TOKENS = 256

# Calibration parameters
# Light bias correction only — NOT aggressive Platt scaling.
# The old _PLATT_A=0.60 was crushing signals toward 0.5.
# Now: just a small intercept shift, slope = 1.0 (identity).
_CALIBRATION_SLOPE = 1.0     # preserve model signal strength
_CALIBRATION_INTERCEPT = 0.0 # no systematic bias correction

# Model registry: (hf_name, weight)
# Rebalanced: ChatGPT-specific detector gets the most weight because
# modern AI text is predominantly ChatGPT/GPT-4 style.
# The academic detector supplements but shouldn't dominate.
MODEL_REGISTRY: list[tuple[str, float]] = [
    ("roberta-base-openai-detector", 0.25),
    ("Hello-SimpleAI/chatgpt-detector-roberta", 0.45),
    ("andreas122001/roberta-academic-detector", 0.30),
]


class AIClassifier:
    """
    Multi-model AI content classifier with ensemble inference.

    Key design decisions:
    - Three models are loaded and run independently.
    - Log-odds pooling: each model's raw P(AI) is converted to log-odds,
      weighted-summed, then converted back to a probability.  This handles
      model disagreement more cleanly than a weighted average.
    - Platt (sigmoid) calibration is applied AFTER pooling.
    - Inference runs in asyncio.to_thread so the sync torch forward pass
      does not block the async event loop under concurrent requests.
    - Per-sentence linguistic features are computed and returned alongside
      the prediction for explainable tooltips.
    """

    def __init__(self):
        self._models: list[dict] = []  # [{model, tokenizer, name, weight}]
        self._loaded = False
        self._model_versions: dict[str, str] = {}

    @property
    def model_versions(self) -> dict[str, str]:
        """Return loaded model name -> revision mapping."""
        return dict(self._model_versions)

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _ensure_models(self):
        """Load all models lazily on first classification call."""
        if self._loaded:
            return
        self._loaded = True

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            torch.set_grad_enabled(False)

            for name, weight in MODEL_REGISTRY:
                try:
                    logger.info(f"Loading AI detection model: {name}")
                    tok = AutoTokenizer.from_pretrained(name)
                    mdl = AutoModelForSequenceClassification.from_pretrained(name)
                    mdl.eval()

                    # Record the actual revision
                    loaded_rev = getattr(mdl.config, '_name_or_path', name)
                    self._model_versions[name] = loaded_rev

                    self._models.append({
                        "model": mdl,
                        "tokenizer": tok,
                        "name": name,
                        "weight": weight,
                    })
                    logger.info(f"Loaded model: {name} (rev={loaded_rev})")
                except Exception as e:
                    logger.warning(f"Could not load model {name}: {e}")

            if not self._models:
                logger.error("CRITICAL: No AI detection models loaded")
            else:
                logger.info(
                    f"Ensemble ready: {len(self._models)} models loaded "
                    f"({', '.join(m['name'] for m in self._models)})"
                )

        except ImportError as e:
            logger.error(f"transformers/torch not installed: {e}")

    # ------------------------------------------------------------------
    # Light calibration (bias correction only)
    # ------------------------------------------------------------------

    @staticmethod
    def _calibrate(raw_ai_prob: float) -> float:
        """
        Apply light calibration to the raw ensemble probability.

        Previous implementation used aggressive Platt scaling (slope=0.60)
        which crushed strong AI signals toward 0.5, causing false negatives.

        Current implementation: identity transform with optional intercept
        shift.  _CALIBRATION_SLOPE=1.0 preserves the full signal from the
        ensemble.  Only adjust _CALIBRATION_INTERCEPT if you observe a
        consistent systematic bias on a held-out validation set.
        """
        p = max(1e-6, min(1 - 1e-6, raw_ai_prob))
        logit = math.log(p / (1 - p))
        cal_logit = _CALIBRATION_SLOPE * logit + _CALIBRATION_INTERCEPT
        return 1.0 / (1.0 + math.exp(-cal_logit))

    # ------------------------------------------------------------------
    # Single-model inference
    # ------------------------------------------------------------------

    def _infer_one(self, text: str, model_entry: dict) -> float:
        """
        Run one model on text, return raw P(AI).

        For texts longer than _WINDOW_SIZE_TOKENS, we use overlapping
        sliding windows and pool results in log-odds space so that the
        full document is considered, not just the first 512 tokens.
        """
        import torch

        tok = model_entry["tokenizer"]
        mdl = model_entry["model"]

        # Detect AI label index dynamically from id2label
        id2label = getattr(mdl.config, "id2label", {})
        ai_index = 1  # safe default
        for idx, label in id2label.items():
            label_lower = str(label).lower()
            if any(kw in label_lower for kw in ("fake", "ai", "machine", "chatgpt", "generated")):
                ai_index = int(idx)
                break

        # Tokenize without truncation to check length
        all_ids = tok.encode(text, add_special_tokens=False)

        if len(all_ids) <= _WINDOW_SIZE_TOKENS - 2:
            # Short text — single pass
            inputs = tok(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=_WINDOW_SIZE_TOKENS,
                padding=True,
            )
            outputs = mdl(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            return probs[0][ai_index].item()

        # Long text — sliding window with log-odds pooling
        window_size = _WINDOW_SIZE_TOKENS - 2  # reserve for [CLS] and [SEP]
        stride = _WINDOW_STRIDE_TOKENS
        logit_sum = 0.0
        weight_sum = 0.0

        start = 0
        while start < len(all_ids):
            end = min(start + window_size, len(all_ids))
            window_ids = all_ids[start:end]

            # Manually add special tokens
            input_ids = [tok.cls_token_id] + window_ids + [tok.sep_token_id]
            attention_mask = [1] * len(input_ids)

            inputs = {
                "input_ids": torch.tensor([input_ids]),
                "attention_mask": torch.tensor([attention_mask]),
            }
            outputs = mdl(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            p = probs[0][ai_index].item()

            # Clamp
            p = max(1e-6, min(1 - 1e-6, p))
            logit = math.log(p / (1 - p))
            # Weight by window size (fuller windows are more reliable)
            w = len(window_ids) / window_size
            logit_sum += logit * w
            weight_sum += w

            start += stride
            if end >= len(all_ids):
                break

        pooled_logit = logit_sum / weight_sum if weight_sum > 0 else 0.0
        return 1.0 / (1.0 + math.exp(-pooled_logit))

    # ------------------------------------------------------------------
    # Log-odds ensemble pooling
    # ------------------------------------------------------------------

    def _ensemble_predict_sync(self, text: str) -> float:
        """
        Run all loaded models, return calibrated P(AI) via log-odds pooling.

        Log-odds pooling:
          logit_i = log(p_i / (1 - p_i))
          pooled_logit = sum(w_i * logit_i) / sum(w_i)
          p_pooled = sigmoid(pooled_logit)

        This is more principled than a weighted average because it operates
        in the unbounded logit space, preventing saturation when one model
        outputs a near-extreme probability.
        """
        if not self._models:
            return 0.5

        total_weight = 0.0
        weighted_logit_sum = 0.0

        for entry in self._models:
            raw = self._infer_one(text, entry)
            # Clamp to avoid log(0)
            raw = max(1e-6, min(1 - 1e-6, raw))
            logit = math.log(raw / (1 - raw))
            w = entry["weight"]
            weighted_logit_sum += logit * w
            total_weight += w

        pooled_logit = weighted_logit_sum / total_weight if total_weight > 0 else 0.0
        raw_ensemble = 1.0 / (1.0 + math.exp(-pooled_logit))
        return self._calibrate(raw_ensemble)

    async def _ensemble_predict(self, text: str) -> float:
        """Async wrapper: runs sync inference in a thread to avoid blocking."""
        return await asyncio.to_thread(self._ensemble_predict_sync, text)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def classify_text(self, text: str) -> tuple[bool, float, str]:
        """
        Classify a single text block.
        Returns (is_ai, confidence, reason).
        """
        self._ensure_models()
        if not self._models:
            return False, 0.5, "No models available"

        try:
            ai_prob = await self._ensemble_predict(text)
            is_ai = ai_prob > 0.5
            confidence = ai_prob if is_ai else (1.0 - ai_prob)

            features = self._compute_sentence_features(text)
            reason = self._build_feature_reason(text, is_ai, confidence, features)
            return is_ai, confidence, reason

        except Exception as e:
            logger.error(f"Classification error: {e}")
            return False, 0.5, "Classification error"

    async def classify_sentences(self, sentences: list[str]) -> list[dict]:
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
            return await self._classify_sentences_windowed(sentences, valid)
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

    async def _classify_sentences_windowed(
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
            ai_prob = await self._ensemble_predict(full_text)
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

        for vi, (_, _sent) in enumerate(valid):
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

        # Per-sentence accumulation across windows using log-odds pooling
        logit_accum = [0.0] * len(valid)
        weight_accum = [0.0] * len(valid)

        for window_indices in windows:
            window_text = " ".join(valid[vi][1] for vi in window_indices)
            ai_prob = await self._ensemble_predict(window_text)
            # Clamp to avoid log(0)
            ai_prob = max(1e-6, min(1 - 1e-6, ai_prob))
            logit = math.log(ai_prob / (1 - ai_prob))
            # Certainty weighting: windows with extreme predictions carry more signal
            certainty = abs(logit) + 0.1

            for vi in window_indices:
                logit_accum[vi] += logit * certainty
                weight_accum[vi] += certainty

        # Build results
        valid_idx_map = {orig_i: vi for vi, (orig_i, _) in enumerate(valid)}
        results = []

        for i, sent in enumerate(all_sentences):
            if not sent.strip():
                continue

            vi = valid_idx_map.get(i)
            if vi is not None and weight_accum[vi] > 0:
                pooled_logit = logit_accum[vi] / weight_accum[vi]
                avg_ai_prob = 1.0 / (1.0 + math.exp(-pooled_logit))
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
