"""
ATS Resume Optimizer Agent.
Generates an optimized version of a resume tailored to a specific job description.

This closes the loop: diagnose (ATS score) → fix (optimized resume) → verify (re-score).
"""
import json
import re
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.models.schemas import GapAnalysis
from app.services.llm_client import LLMClient, get_llm_client

logger = get_logger(__name__)


class ResumeOptimizerAgent:
    """
    Generates an optimized resume given ATS scoring results.

    Produces:
    - An optimized resume text with missing keywords injected naturally
    - A diff showing exactly what changed and why
    - Section-by-section improvement suggestions
    """

    def __init__(self, llm_client: LLMClient | None = None):
        """Initialize resume optimizer agent."""
        self.llm_client = llm_client or get_llm_client()

    @staticmethod
    def _sanitize(text: str, max_len: int = 4000) -> str:
        """Strip prompt-injection markers from user text."""
        sanitized = re.sub(r'(```|---|\*\*\*|###|<\|.*?\|>)', '', text)
        return sanitized[:max_len]

    async def optimize(
        self,
        resume_text: str,
        job_description: str,
        skill_matches: list,
        gap_analysis: dict | GapAnalysis,
        format_score: float,
        keyword_score: float,
    ) -> dict:
        """
        Generate an optimized resume.

        Args:
            resume_text: Original resume text
            job_description: Target job description
            skill_matches: Current skill match results (list of dicts or SkillMatch)
            gap_analysis: Current gap analysis (dict or GapAnalysis)
            format_score: Current format score
            keyword_score: Current keyword match score

        Returns:
            Dict with optimized_text, changes list, and section_improvements
        """
        logger.info("Generating optimized resume")

        # Handle both dict and Pydantic model inputs
        if isinstance(gap_analysis, dict):
            missing_required = gap_analysis.get("missing_required_skills", [])[:10]
            missing_preferred = gap_analysis.get("missing_preferred_skills", [])[:5]
        else:
            missing_required = gap_analysis.missing_required_skills[:10]
            missing_preferred = gap_analysis.missing_preferred_skills[:5]

        matched_skills = []
        for sm in skill_matches:
            if isinstance(sm, dict):
                if sm.get("matched"):
                    matched_skills.append(sm.get("skill", ""))
            elif hasattr(sm, "matched") and sm.matched:
                matched_skills.append(sm.skill)

        # Build targeted optimization prompt
        prompt = f"""You are an expert resume writer and ATS optimization specialist.

ORIGINAL RESUME:
{self._sanitize(resume_text, 3000)}

TARGET JOB DESCRIPTION:
{self._sanitize(job_description, 2000)}

CURRENT ANALYSIS:
- Keyword Match Score: {keyword_score:.0f}/100
- Format Score: {format_score:.0f}/100
- Skills Already Matched: {', '.join(matched_skills[:10]) if matched_skills else 'None'}
- Missing Required Skills: {', '.join(missing_required) if missing_required else 'None'}
- Missing Preferred Skills: {', '.join(missing_preferred) if missing_preferred else 'None'}

TASK: Rewrite the resume to maximize ATS compatibility. Follow these rules:

1. KEEP all factual content (dates, companies, titles, degrees) — do NOT fabricate experience
2. INJECT missing keywords naturally into existing bullet points where truthful
3. ADD a "Skills" section if missing, listing matched + missing skills the candidate likely has
4. USE action verbs at the start of bullets (Led, Developed, Implemented, etc.)
5. QUANTIFY achievements where possible (add placeholders like [X%] if needed)
6. ENSURE standard section headers: Summary, Experience, Education, Skills
7. KEEP the same overall structure and length
8. Do NOT add skills the person clearly doesn't have — only add missing skills that are reasonable given their background

Return ONLY valid JSON:
{{
  "optimized_resume": "The full optimized resume text",
  "changes": [
    {{"section": "section name", "change": "description of what changed", "reason": "why this helps ATS"}},
  ],
  "section_improvements": [
    {{"section": "section name", "before": "original snippet", "after": "optimized snippet", "impact": "high/medium/low"}}
  ],
  "keywords_added": ["keyword1", "keyword2"],
  "estimated_score_improvement": 15
}}"""

        try:
            response = await self.llm_client.complete(
                prompt=prompt,
                temperature=0.5,
                max_tokens=4000,
            )

            # Parse JSON
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
            if not result.get("optimized_resume"):
                raise ValueError("Missing optimized_resume")

            result.setdefault("changes", [])
            result.setdefault("section_improvements", [])
            result.setdefault("keywords_added", [])
            result.setdefault("estimated_score_improvement", 10)

            # Compute a basic diff summary
            result["diff_stats"] = self._compute_diff_stats(
                resume_text, result["optimized_resume"]
            )

            logger.info(
                f"Optimization complete: {len(result['changes'])} changes, "
                f"{len(result['keywords_added'])} keywords added"
            )
            return result

        except Exception as e:
            logger.warning(f"Resume optimization failed: {e}")
            return self._fallback_optimize(
                resume_text, missing_required, missing_preferred, format_score
            )

    def _compute_diff_stats(self, original: str, optimized: str) -> dict:
        """Compute basic statistics about what changed."""
        orig_words = set(original.lower().split())
        opt_words = set(optimized.lower().split())

        added = opt_words - orig_words
        removed = orig_words - opt_words

        orig_lines = original.strip().split('\n')
        opt_lines = optimized.strip().split('\n')

        return {
            "words_added": len(added),
            "words_removed": len(removed),
            "original_line_count": len(orig_lines),
            "optimized_line_count": len(opt_lines),
            "original_word_count": len(original.split()),
            "optimized_word_count": len(optimized.split()),
        }

    def _fallback_optimize(
        self,
        resume_text: str,
        missing_required: list[str],
        missing_preferred: list[str],
        format_score: float,
    ) -> dict:
        """Generate basic optimization when LLM is unavailable."""
        optimized = resume_text

        # Add skills section if missing
        has_skills = bool(re.search(
            r'\b(skills|technical\s+skills|competencies)\b',
            resume_text.lower()
        ))

        if not has_skills and (missing_required or missing_preferred):
            all_skills = missing_required + missing_preferred
            skills_section = "\n\nSKILLS\n" + ", ".join(all_skills[:15])
            optimized += skills_section

        changes = []
        if not has_skills:
            changes.append({
                "section": "Skills",
                "change": "Added Skills section with relevant keywords",
                "reason": "ATS systems look for a dedicated Skills section",
            })

        if format_score < 50:
            changes.append({
                "section": "Format",
                "change": "Consider adding standard section headers (Experience, Education, Skills)",
                "reason": "ATS parsers rely on standard headers to categorize content",
            })

        return {
            "optimized_resume": optimized,
            "changes": changes,
            "section_improvements": [],
            "keywords_added": missing_required[:5],
            "estimated_score_improvement": 5,
            "diff_stats": self._compute_diff_stats(resume_text, optimized),
        }


# ── Singleton ──────────────────────────────────────────────────────────
_optimizer_agent: ResumeOptimizerAgent | None = None


def get_resume_optimizer_agent() -> ResumeOptimizerAgent:
    """Return a singleton ResumeOptimizerAgent."""
    global _optimizer_agent
    if _optimizer_agent is None:
        _optimizer_agent = ResumeOptimizerAgent()
    return _optimizer_agent
