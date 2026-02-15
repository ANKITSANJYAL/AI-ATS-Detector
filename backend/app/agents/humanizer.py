"""
AI Humanizer Agent.
Rewrites AI-flagged sentences to sound naturally human while preserving meaning.

This is the core USP — no competitor does diagnose → fix → verify in one loop.
"""
import json
import re

from app.core.logging import get_logger
from app.services.llm_client import LLMClient, get_llm_client

logger = get_logger(__name__)


class HumanizerAgent:
    """
    Rewrites AI-detected sentences into human-sounding alternatives.

    Design principles:
    - Preserve the original meaning and factual content
    - Add natural human writing patterns (contractions, varied length,
      personal voice, informal transitions)
    - Return multiple rewrite options so the user has choice
    - Provide a brief explanation of what was changed and why
    """

    def __init__(self, llm_client: LLMClient | None = None):
        """Initialize humanizer agent."""
        self.llm_client = llm_client or get_llm_client()

    @staticmethod
    def _sanitize(text: str, max_len: int = 2000) -> str:
        """Strip prompt-injection markers from user text."""
        sanitized = re.sub(r'(```|---|\*\*\*|###|<\|.*?\|>)', '', text)
        return sanitized[:max_len]

    async def humanize_sentence(
        self,
        sentence: str,
        context_before: str = "",
        context_after: str = "",
        tone: str = "natural",
    ) -> dict:
        """
        Rewrite a single AI-flagged sentence to sound human.

        Args:
            sentence: The AI-flagged sentence to rewrite
            context_before: 1-2 sentences before for context
            context_after: 1-2 sentences after for context
            tone: Writing tone — "natural", "casual", "professional", "academic"

        Returns:
            Dict with rewrites list and explanation
        """
        logger.info(f"Humanizing sentence: {sentence[:80]}...")

        tone_instructions = {
            "natural": "Write like a real person — use contractions, vary sentence length, and avoid overly formal language.",
            "casual": "Write in a relaxed, conversational tone — short sentences, contractions, maybe even start with 'And' or 'But'.",
            "professional": "Keep it professional but human — avoid robotic formality, use active voice, be direct.",
            "academic": "Maintain academic rigor but write like a real researcher — vary structure, use first person where appropriate.",
        }

        tone_guide = tone_instructions.get(tone, tone_instructions["natural"])

        prompt = f"""You are a writing coach helping someone rewrite a sentence that was flagged as AI-generated.

ORIGINAL SENTENCE:
"{self._sanitize(sentence)}"

{f'CONTEXT BEFORE: "{self._sanitize(context_before, 500)}"' if context_before else ''}
{f'CONTEXT AFTER: "{self._sanitize(context_after, 500)}"' if context_after else ''}

TONE: {tone}
INSTRUCTIONS: {tone_guide}

Provide 3 different rewrites that:
1. Preserve the EXACT same meaning and facts
2. Sound naturally human (varied sentence length, contractions, active voice)
3. Remove AI tells (formal transitions like "furthermore", "it is important to note", overly uniform structure)
4. Each rewrite should be a different approach (e.g., shorter, restructured, more personal)

Also explain briefly what makes the original sound AI-generated and what you changed.

Return ONLY valid JSON in this exact format:
{{
  "rewrites": [
    "{{"text": "rewrite 1", "approach": "brief label like Shorter or Restructured"}}",
    "{{"text": "rewrite 2", "approach": "brief label"}}",
    "{{"text": "rewrite 3", "approach": "brief label"}}"
  ],
  "explanation": "Brief explanation of AI tells and what was changed",
  "ai_tells": ["tell 1", "tell 2"]
}}"""

        try:
            response = await self.llm_client.complete(
                prompt=prompt,
                temperature=0.8,
                max_tokens=1000,
            )

            # Parse JSON response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            result = json.loads(response)

            # Validate structure
            if not isinstance(result.get("rewrites"), list):
                raise ValueError("Missing rewrites array")

            # Normalize rewrites to ensure consistent structure
            normalized_rewrites = []
            for r in result["rewrites"][:3]:
                if isinstance(r, str):
                    normalized_rewrites.append({"text": r, "approach": "Rewrite"})
                elif isinstance(r, dict) and "text" in r:
                    normalized_rewrites.append({
                        "text": r["text"],
                        "approach": r.get("approach", "Rewrite"),
                    })

            result["rewrites"] = normalized_rewrites
            result.setdefault("explanation", "")
            result.setdefault("ai_tells", [])

            logger.info(f"Generated {len(normalized_rewrites)} rewrites")
            return result

        except Exception as e:
            logger.warning(f"Humanizer failed: {e}")
            return self._fallback_humanize(sentence)

    async def humanize_batch(
        self,
        sentences: list[dict],
        tone: str = "natural",
    ) -> list[dict]:
        """
        Humanize multiple AI-flagged sentences.

        Args:
            sentences: List of dicts with 'text', 'index', optional 'context_before'/'context_after'
            tone: Writing tone

        Returns:
            List of humanization results, one per input sentence
        """
        logger.info(f"Batch humanizing {len(sentences)} sentences")

        results = []
        for sent in sentences[:20]:  # Cap at 20 to avoid API overload
            result = await self.humanize_sentence(
                sentence=sent["text"],
                context_before=sent.get("context_before", ""),
                context_after=sent.get("context_after", ""),
                tone=tone,
            )
            result["original_index"] = sent.get("index", 0)
            result["original_text"] = sent["text"]
            results.append(result)

        return results

    def _fallback_humanize(self, sentence: str) -> dict:
        """Generate basic humanization when LLM is unavailable."""
        # Simple heuristic rewrites
        text = sentence

        # Replace formal transitions
        replacements = {
            "Furthermore, ": "Also, ",
            "Moreover, ": "Plus, ",
            "Additionally, ": "On top of that, ",
            "Consequently, ": "So, ",
            "Subsequently, ": "Then, ",
            "It is important to note that ": "",
            "It should be noted that ": "",
            "In conclusion, ": "To wrap up, ",
            "In summary, ": "All in all, ",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        return {
            "rewrites": [
                {"text": text, "approach": "Basic cleanup"},
            ],
            "explanation": "Applied basic transition word replacements. For better results, ensure the LLM service is available.",
            "ai_tells": ["Formal transition words detected"],
        }


# ── Singleton ──────────────────────────────────────────────────────────
_humanizer_agent: HumanizerAgent | None = None


def get_humanizer_agent() -> HumanizerAgent:
    """Return a singleton HumanizerAgent."""
    global _humanizer_agent
    if _humanizer_agent is None:
        _humanizer_agent = HumanizerAgent()
    return _humanizer_agent
