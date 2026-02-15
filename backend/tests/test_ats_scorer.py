"""
Test suite for ATS Scorer Agent.
Validates scoring accuracy using Spearman's Rho correlation.
"""
import numpy as np
import pytest

from app.agents.ats_scorer import ATSScorerAgent


def spearman_correlation(x: list[float], y: list[float]) -> tuple[float, float]:
    """
    Calculate Spearman's rank correlation coefficient.

    Args:
        x: First dataset
        y: Second dataset

    Returns:
        Tuple of (correlation coefficient, p-value approximation)
    """
    n = len(x)

    # Rank the data
    x_ranks = np.argsort(np.argsort(x)) + 1
    y_ranks = np.argsort(np.argsort(y)) + 1

    # Calculate Spearman's rho
    d_squared = np.sum((x_ranks - y_ranks) ** 2)
    rho = 1 - (6 * d_squared) / (n * (n**2 - 1))

    # Approximate p-value using t-distribution approximation
    t_stat = rho * np.sqrt((n - 2) / (1 - rho**2)) if abs(rho) < 1 else float('inf')

    # Rough p-value approximation (for n > 5)
    # For exact p-values, use scipy.stats.t.sf
    if abs(t_stat) > 2.776:  # Critical value for p < 0.05, df = 5
        p_value = 0.01
    elif abs(t_stat) > 2.015:  # Critical value for p < 0.1, df = 5
        p_value = 0.05
    else:
        p_value = 0.1

    return rho, p_value


class TestATSScorerValidation:
    """
    Validation test suite for ATS scoring accuracy.
    Uses Spearman's Rho to measure correlation with ground truth.
    """

    @pytest.fixture
    def ats_scorer(self) -> ATSScorerAgent:
        """Get ATS scorer instance."""
        return ATSScorerAgent()

    @pytest.fixture
    def test_cases(self) -> list[dict]:
        """
        Test cases with ground truth scores.
        In production, these would be loaded from database.
        """
        return [
            {
                "resume": "Software Engineer with 5 years of Python, Django, and PostgreSQL experience. Built scalable APIs and microservices. Strong in cloud architecture (AWS).",
                "job_description": {
                    "description": "We're seeking a Senior Backend Engineer with expertise in Python, Django, PostgreSQL, and AWS to build scalable systems.",
                    "required_skills": ["Python", "Django", "PostgreSQL"],
                    "preferred_skills": ["AWS", "Microservices", "API Design"],
                },
                "expected_score": 92.0,  # High match
            },
            {
                "resume": "Frontend Developer specializing in React, TypeScript, and modern JavaScript. 3 years experience building responsive web applications.",
                "job_description": {
                    "description": "Looking for a Senior Backend Engineer with Python and Django experience to build REST APIs.",
                    "required_skills": ["Python", "Django", "REST API"],
                    "preferred_skills": ["PostgreSQL", "Docker"],
                },
                "expected_score": 25.0,  # Low match (different specialization)
            },
            {
                "resume": "Data Scientist with expertise in Python, machine learning, and data analysis. Proficient in Pandas, NumPy, and scikit-learn.",
                "job_description": {
                    "description": "Data Scientist position requiring Python, machine learning, and statistical analysis skills.",
                    "required_skills": ["Python", "Machine Learning", "Statistics"],
                    "preferred_skills": ["Pandas", "NumPy", "SQL"],
                },
                "expected_score": 88.0,  # High match
            },
            {
                "resume": "Full Stack Developer with experience in JavaScript, Node.js, React, and MongoDB. Built several web applications.",
                "job_description": {
                    "description": "Full Stack Engineer needed with JavaScript, Node.js, React, and database experience.",
                    "required_skills": ["JavaScript", "Node.js", "React"],
                    "preferred_skills": ["MongoDB", "REST API"],
                },
                "expected_score": 90.0,  # High match
            },
            {
                "resume": "Marketing Manager with 7 years experience in digital marketing, SEO, and content strategy.",
                "job_description": {
                    "description": "Software Engineer position requiring Java, Spring Boot, and microservices expertise.",
                    "required_skills": ["Java", "Spring Boot", "Microservices"],
                    "preferred_skills": ["Kubernetes", "Docker"],
                },
                "expected_score": 15.0,  # Very low match (completely different field)
            },
        ]

    @pytest.mark.asyncio
    async def test_ats_scoring_accuracy(
        self,
        ats_scorer: ATSScorerAgent,
        test_cases: list[dict]
    ):
        """
        Test ATS scoring accuracy using Spearman's Rho correlation.

        Validates that the scorer's predictions correlate with ground truth scores.
        Success criteria: Spearman's Rho > 0.7
        """
        predicted_scores = []
        expected_scores = []

        for i, test_case in enumerate(test_cases):
            # Perform scoring
            result = await ats_scorer.analyze(
                document_id=f"test_doc_{i}",
                job_id=f"test_job_{i}",
                resume_text=test_case["resume"],
                job_description=test_case["job_description"],
            )

            predicted_scores.append(result.overall_score)
            expected_scores.append(test_case["expected_score"])

            print(f"\nTest Case {i+1}:")
            print(f"  Expected Score: {test_case['expected_score']:.1f}")
            print(f"  Predicted Score: {result.overall_score:.1f}")
            print(f"  Difference: {abs(result.overall_score - test_case['expected_score']):.1f}")

        # Calculate Spearman's Rho
        correlation, p_value = spearman_correlation(predicted_scores, expected_scores)

        print(f"\n{'='*60}")
        print("VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"Spearman's Rho: {correlation:.4f}")
        print(f"P-value: {p_value:.4f}")
        print(f"{'='*60}\n")

        # Assert correlation meets threshold
        assert correlation > 0.7, (
            f"Spearman's Rho ({correlation:.4f}) below threshold (0.7). "
            "Model predictions do not correlate sufficiently with ground truth."
        )

        # Assert statistical significance
        assert p_value < 0.05, (
            f"P-value ({p_value:.4f}) not statistically significant (threshold: 0.05)"
        )

    @pytest.mark.asyncio
    async def test_skill_matching_accuracy(
        self,
        ats_scorer: ATSScorerAgent
    ):
        """Test skill matching component accuracy."""
        resume_text = "Python Django PostgreSQL AWS Docker Kubernetes"
        skills = ["Python", "Django", "PostgreSQL", "AWS", "Docker", "Java"]

        matches = await ats_scorer._match_skills(resume_text, skills)

        # Verify correct matches
        skill_results = {match.skill: match.matched for match in matches}

        assert skill_results["Python"] is True
        assert skill_results["Django"] is True
        assert skill_results["PostgreSQL"] is True
        assert skill_results["AWS"] is True
        assert skill_results["Docker"] is True
        assert skill_results["Java"] is False

        print("\nSkill Matching Test Passed:")
        for match in matches:
            print(f"  {match.skill}: {'✓' if match.matched else '✗'}")

    @pytest.mark.asyncio
    async def test_score_boundaries(
        self,
        ats_scorer: ATSScorerAgent
    ):
        """Test that scores are within valid boundaries (0-100)."""
        test_cases = [
            ("Perfect match with all keywords", {"description": "keywords", "required_skills": [], "preferred_skills": []}),
            ("No match at all", {"description": "completely different", "required_skills": [], "preferred_skills": []}),
        ]

        for resume, job_desc in test_cases:
            result = await ats_scorer.analyze(
                document_id="boundary_test",
                job_id="boundary_test",
                resume_text=resume,
                job_description=job_desc,
            )

            assert 0 <= result.overall_score <= 100, (
                f"Score {result.overall_score} outside valid range [0, 100]"
            )
            assert 0 <= result.keyword_match_score <= 100
            assert 0 <= result.semantic_similarity_score <= 100
            assert 0 <= result.format_score <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
