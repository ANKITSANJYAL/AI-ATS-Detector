"""
ATS Scoring Agent.
Performs semantic analysis and scoring for ATS compatibility.
"""
import json
import re
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.models.schemas import (
    ATSScoringResponse,
    GapAnalysis,
    SkillMatch,
)
from app.services.llm_client import LLMClient, get_llm_client

logger = get_logger(__name__)


class ATSScorerAgent:
    """
    ATS scoring agent for resume analysis.
    Performs keyword matching, semantic analysis, and gap identification.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        """Initialize ATS scorer agent."""
        self.llm_client = llm_client or get_llm_client()

    @staticmethod
    def _sanitize_for_prompt(text: str, max_len: int = 3000) -> str:
        """Strip potential prompt-injection markers from user-supplied text."""
        # Remove sequences that look like system/instruction delimiters
        sanitized = re.sub(r'(```|---|\*\*\*|###|<\|.*?\|>)', '', text)
        return sanitized[:max_len]

    async def extract_skills_from_job(self, job_description: str) -> dict:
        """
        Extract required and preferred skills from job description using LLM.

        Args:
            job_description: Raw job description text

        Returns:
            Dictionary with required_skills and preferred_skills arrays
        """
        prompt = f"""Analyze this job description and extract the skills. Return ONLY a valid JSON object with two arrays:

Job Description:
{self._sanitize_for_prompt(job_description, 3000)}

Return format:
{{
  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["skill3", "skill4", ...]
}}

Guidelines:
- required_skills: Must-have technical skills, years of experience, certifications, core competencies
- preferred_skills: Nice-to-have skills, bonus qualifications, soft skills
- Use concise skill names (e.g., "Python", "React", "5+ years experience", "Team Leadership")
- Extract 5-15 required skills and 3-10 preferred skills
- Return ONLY the JSON object, no additional text"""

        try:
            response = await self.llm_client.complete(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1000,
            )

            # Clean response - extract JSON if wrapped in markdown
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            skills_data = json.loads(response)

            # Validate structure
            if not isinstance(skills_data.get("required_skills"), list):
                skills_data["required_skills"] = []
            if not isinstance(skills_data.get("preferred_skills"), list):
                skills_data["preferred_skills"] = []

            logger.info(
                f"Extracted {len(skills_data['required_skills'])} required and "
                f"{len(skills_data['preferred_skills'])} preferred skills"
            )

            return skills_data

        except Exception as e:
            logger.warning(f"Failed to extract skills from job description: {e}")
            # Fallback: basic keyword extraction
            return self._fallback_skill_extraction(job_description)

    def _fallback_skill_extraction(self, job_description: str) -> dict:
        """
        Fallback skill extraction using pattern matching.

        Args:
            job_description: Job description text

        Returns:
            Dictionary with required_skills and preferred_skills
        """
        # Common tech skills patterns
        tech_skills = [
            "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Ruby", "Go", "Rust",
            "React", "Angular", "Vue", "Node.js", "Django", "Flask", "FastAPI",
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
            "AWS", "Azure", "GCP", "Git", "CI/CD", "REST API", "GraphQL",
            "Machine Learning", "AI", "Data Science", "TensorFlow", "PyTorch",
        ]

        found_skills = []
        text_lower = job_description.lower()

        for skill in tech_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)

        # Split into required (first 70%) and preferred (rest)
        split_point = max(1, int(len(found_skills) * 0.7))

        return {
            "required_skills": found_skills[:split_point] if found_skills else ["Relevant experience"],
            "preferred_skills": found_skills[split_point:] if len(found_skills) > split_point else [],
        }

    async def analyze(
        self,
        document_id: str,
        job_id: str,
        resume_text: str,
        job_description: dict,
    ) -> ATSScoringResponse:
        """
        Perform comprehensive ATS scoring analysis.

        Args:
            document_id: Resume document identifier
            job_id: Job description identifier
            resume_text: Resume text content
            job_description: Job description data

        Returns:
            ATS scoring analysis results
        """
        logger.info(f"Starting ATS scoring for document {document_id} against job {job_id}")

        # Extract job requirements
        job_text = job_description["description"]
        required_skills = job_description.get("required_skills", [])
        preferred_skills = job_description.get("preferred_skills", [])

        # Generate embeddings for semantic similarity
        resume_embedding = await self.llm_client.embed(resume_text[:8000])
        job_embedding = await self.llm_client.embed(job_text[:8000])

        # Calculate semantic similarity
        semantic_score = self._calculate_similarity(resume_embedding, job_embedding)

        # Keyword matching
        keyword_score = self._calculate_keyword_match(resume_text, job_text)

        # Format analysis
        format_score = self._analyze_format(resume_text)

        # Skill matching
        skill_matches = await self._match_skills(
            resume_text,
            required_skills + preferred_skills
        )

        # Gap analysis
        gap_analysis = await self._analyze_gaps(
            resume_text,
            required_skills,
            preferred_skills,
            skill_matches,
        )

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            semantic_score,
            keyword_score,
            format_score,
            skill_matches,
        )

        logger.info(
            f"ATS scoring complete for {document_id}: {overall_score:.1f}/100"
        )

        return ATSScoringResponse(
            document_id=document_id,
            job_id=job_id,
            overall_score=overall_score,
            keyword_match_score=keyword_score,
            semantic_similarity_score=semantic_score,
            format_score=format_score,
            skill_matches=skill_matches,
            gap_analysis=gap_analysis,
            analysis_timestamp=datetime.now(UTC),
        )

    def _calculate_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float]
    ) -> float:
        """
        Calculate cosine similarity between embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-100)
        """
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5

        similarity = dot_product / (magnitude1 * magnitude2) if magnitude1 and magnitude2 else 0

        # Convert to 0-100 scale
        return (similarity + 1) * 50  # Cosine similarity ranges from -1 to 1

    def _calculate_keyword_match(
        self,
        resume_text: str,
        job_text: str
    ) -> float:
        """
        Calculate keyword matching score.

        Args:
            resume_text: Resume content
            job_text: Job description content

        Returns:
            Keyword match score (0-100)
        """
        # Extract important keywords from job description
        job_words = set(self._extract_keywords(job_text))
        resume_words = set(self._extract_keywords(resume_text))

        if not job_words:
            return 0.0

        # Calculate match percentage
        matches = len(job_words & resume_words)
        match_percentage = (matches / len(job_words)) * 100

        return min(100.0, match_percentage)

    def _extract_keywords(self, text: str) -> list[str]:
        """
        Extract keywords from text, including multi-word terms, acronyms,
        and short technology names.
        """
        text_lower = text.lower()

        # Remove common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'for', 'with', 'from', 'this', 'that',
            'have', 'has', 'had', 'will', 'would', 'should', 'could', 'may',
            'can', 'are', 'was', 'were', 'been', 'being', 'into', 'through',
            'about', 'also', 'our', 'your', 'their', 'they', 'who', 'what',
            'when', 'where', 'which', 'not', 'all', 'any', 'each', 'more',
        }

        # 1. Extract multi-word technical terms (e.g. "machine learning", "node.js")
        multi_word = re.findall(
            r'\b[a-z][a-z.+#]+(?:\s+[a-z][a-z.+#]+){1,3}\b', text_lower
        )
        multi_word = [t for t in multi_word if not all(w in stop_words for w in t.split())]

        # 2. Extract single words (including short ones like "go", "ai", "c#", "r")
        single_words = re.findall(r'\b[a-z#.+]{2,}\b', text_lower)
        single_words = [w for w in single_words if w not in stop_words]

        # 3. Extract uppercase acronyms from original text (AWS, GCP, CI/CD)
        acronyms = re.findall(r'\b[A-Z][A-Z0-9/]{1,10}\b', text)
        acronyms = [a.lower() for a in acronyms]

        return list(set(multi_word + single_words + acronyms))

    def _analyze_format(self, resume_text: str) -> float:
        """
        Analyze resume format and structure.

        Args:
            resume_text: Resume content

        Returns:
            Format score (0-100)
        """
        score = 0.0

        # Check for common sections
        sections = [
            r'\b(experience|work history|employment)\b',
            r'\b(education|academic)\b',
            r'\b(skills|competencies|expertise)\b',
            r'\b(summary|objective|profile)\b',
        ]

        for pattern in sections:
            if re.search(pattern, resume_text.lower()):
                score += 25.0

        # Check for dates (indicates work history)
        if re.search(r'\b(20\d{2}|19\d{2})\b', resume_text):
            score += 10.0

        # Check for contact information
        if re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', resume_text):  # Email
            score += 10.0

        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', resume_text):  # Phone
            score += 10.0

        return min(100.0, score)

    async def _match_skills(
        self,
        resume_text: str,
        skills: list[str]
    ) -> list[SkillMatch]:
        """
        Match skills against resume using word-boundary-aware matching.
        Fixes: "Java" no longer matches "JavaScript".
        """
        if not skills:
            return []

        skill_matches = []
        resume_lower = resume_text.lower()

        for skill in skills:
            skill_lower = skill.lower()

            # Build a word-boundary regex for the exact skill phrase.
            # re.escape handles special chars like "C++", "C#", "Node.js"
            pattern = r'(?<![a-z])' + re.escape(skill_lower) + r'(?![a-z])'
            matched = bool(re.search(pattern, resume_lower))
            relevance = 1.0 if matched else 0.0

            # Fuzzy matching: check how many individual words appear
            if not matched:
                skill_words = skill_lower.split()
                word_matches = sum(
                    1 for word in skill_words
                    if len(word) > 2 and re.search(r'(?<![a-z])' + re.escape(word) + r'(?![a-z])', resume_lower)
                )
                if skill_words and word_matches > 0:
                    relevance = word_matches / len(skill_words)
                    matched = relevance >= 0.6

            # Check known variations if still not matched
            if not matched:
                variations = self._get_skill_variations(skill_lower)
                for variant in variations:
                    vp = r'(?<![a-z])' + re.escape(variant) + r'(?![a-z])'
                    if re.search(vp, resume_lower):
                        matched = True
                        relevance = 0.9
                        break

            skill_matches.append(
                SkillMatch(
                    skill=skill,
                    matched=matched,
                    relevance=relevance,
                )
            )

        return skill_matches

    def _get_skill_variations(self, skill: str) -> list[str]:
        """
        Get common variations of a skill name.

        Args:
            skill: Original skill name

        Returns:
            List of skill variations
        """
        variations = []
        skill_lower = skill.lower()

        # Programming languages
        variation_map = {
            "python": ["python3", "python 3", "py"],
            "javascript": ["js", "ecmascript", "es6", "es2015"],
            "typescript": ["ts"],
            "java": ["java se", "java ee"],
            "c++": ["cpp", "c plus plus"],
            "c#": ["csharp", "c sharp"],
            "node.js": ["nodejs", "node"],
            "react": ["reactjs", "react.js"],
            "vue": ["vuejs", "vue.js"],
            "angular": ["angularjs"],
        }

        # Add mapped variations
        if skill_lower in variation_map:
            variations.extend(variation_map[skill_lower])

        # Add variations with common suffixes/prefixes
        if " " in skill_lower:
            variations.append(skill_lower.replace(" ", ""))
            variations.append(skill_lower.replace(" ", "-"))
            variations.append(skill_lower.replace(" ", "_"))

        return variations

    async def _analyze_gaps(
        self,
        resume_text: str,
        required_skills: list[str],
        preferred_skills: list[str],
        skill_matches: list[SkillMatch],
    ) -> GapAnalysis:
        """
        Analyze skills gaps and provide recommendations.

        Args:
            resume_text: Resume content
            required_skills: Required skills list
            preferred_skills: Preferred skills list
            skill_matches: Skill matching results

        Returns:
            Gap analysis with recommendations
        """
        # Identify missing skills
        skill_match_dict = {sm.skill: sm.matched for sm in skill_matches}

        missing_required = [
            skill for skill in required_skills
            if not skill_match_dict.get(skill, False)
        ]

        missing_preferred = [
            skill for skill in preferred_skills
            if not skill_match_dict.get(skill, False)
        ]

        # Generate recommendations using LLM
        recommendations_prompt = f"""Analyze this resume and provide 5 specific, actionable recommendations to improve ATS compatibility.

Resume excerpt: {self._sanitize_for_prompt(resume_text, 1500)}...

Missing Required Skills: {', '.join(missing_required[:10]) if missing_required else 'None'}
Missing Preferred Skills: {', '.join(missing_preferred[:5]) if missing_preferred else 'None'}

Provide recommendations in these categories:
1. Add missing critical skills (if any)
2. Improve keyword optimization
3. Enhance formatting for ATS readability
4. Quantify achievements with metrics
5. Strengthen technical descriptions

Return ONLY a JSON array of 5 strings (no other text):
["recommendation 1", "recommendation 2", "recommendation 3", "recommendation 4", "recommendation 5"]"""

        try:
            response = await self.llm_client.complete(
                prompt=recommendations_prompt,
                temperature=0.7,
                max_tokens=600,
            )

            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            recommendations = json.loads(response)

            if not isinstance(recommendations, list):
                raise ValueError("Recommendations must be a list")

        except Exception as e:
            logger.warning(f"Failed to generate recommendations: {e}")
            # Smart fallback based on actual gaps
            recommendations = self._generate_fallback_recommendations(
                missing_required,
                missing_preferred,
                resume_text
            )

        return GapAnalysis(
            missing_required_skills=missing_required,
            missing_preferred_skills=missing_preferred,
            recommendations=recommendations[:5],
        )

    def _generate_fallback_recommendations(
        self,
        missing_required: list[str],
        missing_preferred: list[str],
        resume_text: str
    ) -> list[str]:
        """
        Generate fallback recommendations when LLM fails.

        Args:
            missing_required: Missing required skills
            missing_preferred: Missing preferred skills
            resume_text: Resume content

        Returns:
            List of recommendations
        """
        recommendations = []

        # Skill-based recommendations
        if missing_required:
            top_missing = missing_required[:3]
            recommendations.append(
                f"Add experience with: {', '.join(top_missing)}. Include specific projects or achievements."
            )

        if missing_preferred:
            recommendations.append(
                f"Consider highlighting: {', '.join(missing_preferred[:2])} to strengthen your profile."
            )

        # Format recommendations
        if not re.search(r'\b(experience|work history|employment)\b', resume_text.lower()):
            recommendations.append(
                "Add a clear 'Work Experience' section with job titles, companies, and dates."
            )

        # Quantification check
        if len(re.findall(r'\b\d+%|\b\d+x\b|\$\d+', resume_text)) < 3:
            recommendations.append(
                "Quantify your achievements with metrics (e.g., '30% improvement', '10+ projects')."
            )

        # Keyword density
        recommendations.append(
            "Mirror keywords from the job description in your experience bullets for better ATS matching."
        )

        # Always provide action verbs tip
        recommendations.append(
            "Use strong action verbs (e.g., 'Led', 'Developed', 'Implemented') to start bullet points."
        )

        return recommendations[:5]

    def _calculate_overall_score(
        self,
        semantic_score: float,
        keyword_score: float,
        format_score: float,
        skill_matches: list[SkillMatch],
    ) -> float:
        """
        Calculate overall ATS score.

        Args:
            semantic_score: Semantic similarity score
            keyword_score: Keyword matching score
            format_score: Format quality score
            skill_matches: Skill matching results

        Returns:
            Overall ATS score (0-100)
        """
        # Calculate skill match percentage
        if skill_matches:
            matched_count = sum(1 for sm in skill_matches if sm.matched)
            skill_score = (matched_count / len(skill_matches)) * 100
        else:
            skill_score = 50.0  # Neutral score if no skills specified

        # Weighted average
        overall = (
            semantic_score * 0.3 +
            keyword_score * 0.3 +
            format_score * 0.2 +
            skill_score * 0.2
        )

        return min(100.0, overall)


# ── Singleton ──────────────────────────────────────────────────────────
_ats_scorer_agent: ATSScorerAgent | None = None


def get_ats_scorer_agent() -> ATSScorerAgent:
    """Return a singleton ATSScorerAgent."""
    global _ats_scorer_agent
    if _ats_scorer_agent is None:
        _ats_scorer_agent = ATSScorerAgent()
    return _ats_scorer_agent
