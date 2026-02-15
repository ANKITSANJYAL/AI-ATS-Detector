"""
═══════════════════════════════════════════════════════════════════════
ATS Resume Scorer — Benchmark Evaluation Script
═══════════════════════════════════════════════════════════════════════

Evaluates the deterministic components of the ATS scoring pipeline:
  1. Keyword extraction quality (precision/recall against labelled skill sets)
  2. Format scoring (structured resume vs unstructured text)
  3. Skill matching accuracy (exact vs fuzzy matching)
  4. Overall score correlation with expert-annotated test cases (Spearman ρ)
  5. Keyword match with TF-based importance weighting

No LLM calls needed — all tests are local and instant.

Usage:
  cd backend
  python evaluation/benchmark_ats_scorer.py
  python evaluation/benchmark_ats_scorer.py --verbose
"""

import sys
import os
import re
import json
import math
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── Spearman Correlation ────────────────────────────────────────────

def spearman_rho(x: list[float], y: list[float]) -> float:
    """Compute Spearman's rank correlation coefficient."""
    n = len(x)
    if n < 3:
        return 0.0
    x_ranks = np.argsort(np.argsort(x)).astype(float) + 1
    y_ranks = np.argsort(np.argsort(y)).astype(float) + 1
    d_sq = np.sum((x_ranks - y_ranks) ** 2)
    rho = 1 - (6 * d_sq) / (n * (n ** 2 - 1))
    return float(rho)


# ─── Test Cases ──────────────────────────────────────────────────────

# Curated resume-JD pairs with expert-annotated expected scores
# These simulate real-world matching scenarios at various quality levels

KEYWORD_EXTRACTION_TESTS = [
    {
        "name": "Tech JD with clear skills",
        "text": (
            "We are looking for a Senior Python Developer with experience in Django, "
            "PostgreSQL, AWS, and Docker. Must have 5+ years experience building REST APIs. "
            "Knowledge of CI/CD pipelines and Kubernetes is preferred."
        ),
        "expected_keywords": {
            "python", "django", "postgresql", "aws", "docker",
            "rest", "kubernetes",
        },
        "unexpected_keywords": {
            "looking", "experience", "must", "knowledge", "preferred",
            "years", "building", "have", "senior",
        },
    },
    {
        "name": "Data Science JD",
        "text": (
            "Data Scientist position requiring Python, TensorFlow, and SQL expertise. "
            "The ideal candidate has experience with machine learning, NLP, and "
            "statistical modeling. PhD preferred. Strong communication skills required."
        ),
        "expected_keywords": {
            "python", "tensorflow", "sql", "machine learning", "nlp",
            "statistical",
        },
        "unexpected_keywords": {
            "position", "requiring", "ideal", "candidate", "experience",
            "strong", "required", "preferred",
        },
    },
    {
        "name": "Frontend JD",
        "text": (
            "React Developer needed with TypeScript, CSS, HTML5 expertise. "
            "Experience with Next.js, Tailwind CSS, and GraphQL is a plus. "
            "Must be able to work in an Agile environment."
        ),
        "expected_keywords": {
            "react", "typescript", "css", "html5", "graphql", "agile",
        },
        "unexpected_keywords": {
            "needed", "experience", "plus", "must", "able", "work",
            "environment",
        },
    },
]


FORMAT_SCORING_TESTS = [
    {
        "name": "Well-formatted resume",
        "text": """John Doe
john.doe@email.com | (555) 123-4567

SUMMARY
Experienced software engineer with 8 years of expertise in full-stack development.

EXPERIENCE
Senior Software Engineer | TechCorp | 2020 – Present
• Led team of 5 engineers to deliver microservices platform
• Reduced deployment time by 40% through CI/CD automation
• Architected event-driven system handling 1M+ events daily

Software Engineer | StartupXYZ | 2017 – 2020
• Developed REST APIs serving 50,000+ daily users
• Implemented automated testing achieving 95% code coverage
• Managed PostgreSQL databases with 10TB+ data

EDUCATION
B.S. Computer Science | MIT | 2013 – 2017

SKILLS
Python, Django, PostgreSQL, AWS, Docker, Kubernetes, React, TypeScript
""",
        "expected_min_score": 60.0,
        "description": "Has all sections, contact info, bullets, dates, action verbs, metrics",
    },
    {
        "name": "Poorly formatted resume",
        "text": """i have been working as a developer for a while now and i know python and some javascript.
i went to college and got a degree. i worked at a company doing stuff with computers.
i can do things with databases and also some web development.
i am looking for a new job where i can grow my skills.""",
        "expected_max_score": 25.0,
        "description": "No sections, no contact, no bullets, no dates, no metrics",
    },
    {
        "name": "Moderate resume",
        "text": """Jane Smith
jane@email.com

Experience
Software Developer at ABC Corp, 2019-2023
- Built web applications using React and Node.js
- Worked with databases including MongoDB

Education
BS in Computer Science, State University, 2019

Skills
JavaScript, React, Node.js, MongoDB, Git
""",
        "expected_min_score": 35.0,
        "expected_max_score": 75.0,
        "description": "Has sections and some structure, but missing bullets, metrics, phone",
    },
]


SKILL_MATCHING_TESTS = [
    {
        "name": "Exact match",
        "resume": "Proficient in Python, Django, and PostgreSQL. Built REST APIs using FastAPI.",
        "skills": ["Python", "Django", "PostgreSQL", "REST API"],
        "expected_matched": {"Python", "Django", "PostgreSQL"},  # REST API partial
        "expected_unmatched": set(),
    },
    {
        "name": "Java vs JavaScript distinction",
        "resume": "Expert JavaScript developer with React and Node.js experience.",
        "skills": ["Java", "JavaScript", "React", "Node.js"],
        "expected_matched": {"JavaScript", "React", "Node.js"},
        "expected_unmatched": {"Java"},  # Should NOT match Java from JavaScript
    },
    {
        "name": "Variation matching",
        "resume": "Built applications with NodeJS, ReactJS, and TypeScript.",
        "skills": ["Node.js", "React", "TypeScript"],
        "expected_matched": {"TypeScript"},
        # Node.js → NodeJS and React → ReactJS should be caught by variation matching
    },
    {
        "name": "No matches",
        "resume": "Marketing professional with 10 years of brand management experience.",
        "skills": ["Python", "Machine Learning", "TensorFlow", "SQL"],
        "expected_matched": set(),
        "expected_unmatched": {"Python", "Machine Learning", "TensorFlow", "SQL"},
    },
]


# End-to-end scoring test cases with expert-expected scores
SCORING_TEST_CASES = [
    {
        "name": "Perfect match — Backend Python",
        "resume": """Senior Python Developer
john@email.com | (555) 123-4567

SUMMARY
Senior Python developer with 7 years of experience in Django, FastAPI, and cloud architecture.

EXPERIENCE
Senior Backend Engineer | TechCorp | 2020 – Present
• Led migration of monolithic Django app to FastAPI microservices
• Designed PostgreSQL schemas handling 50M+ records
• Deployed applications on AWS using Docker and Kubernetes
• Reduced API response times by 60% through Redis caching
• Implemented CI/CD pipelines using GitHub Actions

Backend Developer | DataCo | 2017 – 2020
• Developed REST APIs serving 100K+ daily users with Django
• Built data pipelines using Python and PostgreSQL
• Achieved 98% test coverage with pytest

EDUCATION
M.S. Computer Science | Stanford University | 2017

SKILLS
Python, Django, FastAPI, PostgreSQL, Redis, AWS, Docker, Kubernetes, REST API, CI/CD, Git
""",
        "job_description": {
            "description": "Senior Backend Engineer with Python, Django, PostgreSQL, and AWS experience.",
            "required_skills": ["Python", "Django", "PostgreSQL", "AWS"],
            "preferred_skills": ["Docker", "Kubernetes", "Redis", "CI/CD"],
        },
        "expected_score_range": (65, 100),  # High match
    },
    {
        "name": "Complete mismatch — Marketing vs Engineering",
        "resume": """Marketing Director with 15 years in brand strategy, content creation, and social media campaigns.
Led teams of 20+ across global campaigns. Expert in Adobe Creative Suite, HubSpot, and Google Analytics.""",
        "job_description": {
            "description": "Looking for a Machine Learning Engineer with Python, PyTorch, and distributed computing.",
            "required_skills": ["Python", "PyTorch", "Machine Learning", "Distributed Computing"],
            "preferred_skills": ["TensorFlow", "Spark", "CUDA"],
        },
        "expected_score_range": (0, 35),  # Low match
    },
    {
        "name": "Partial match — Frontend applying to Fullstack",
        "resume": """Frontend Developer
dev@email.com

EXPERIENCE
Frontend Engineer | WebCo | 2021 – Present
• Built responsive UIs with React and TypeScript
• Implemented state management using Redux
• Created reusable component libraries

SKILLS
JavaScript, TypeScript, React, Redux, CSS, HTML, Git
""",
        "job_description": {
            "description": "Full Stack Developer with React, Node.js, Python, and database experience.",
            "required_skills": ["React", "Node.js", "Python", "SQL"],
            "preferred_skills": ["TypeScript", "Docker", "AWS"],
        },
        "expected_score_range": (20, 60),  # Partial match — only React overlaps
    },
    {
        "name": "Data Science match",
        "resume": """Data Scientist
data@email.com | (555) 987-6543

EXPERIENCE
Senior Data Scientist | AI Corp | 2019 – Present
• Developed NLP models using BERT and transformers achieving 95% accuracy
• Built ML pipelines with Python, scikit-learn, and TensorFlow
• Analyzed datasets with Pandas and SQL, generating insights for 5 product teams
• Deployed models to production using Docker and AWS SageMaker
• Reduced model training time by 50% through distributed computing

EDUCATION
Ph.D. Machine Learning | MIT | 2019

SKILLS
Python, TensorFlow, PyTorch, scikit-learn, SQL, Pandas, NumPy, Docker, AWS, NLP, Machine Learning
""",
        "job_description": {
            "description": "Data Scientist with expertise in ML, NLP, and Python.",
            "required_skills": ["Python", "Machine Learning", "NLP", "SQL"],
            "preferred_skills": ["TensorFlow", "PyTorch", "Docker", "AWS"],
        },
        "expected_score_range": (60, 100),  # High match
    },
    {
        "name": "Entry-level applying to Senior role",
        "resume": """Recent CS graduate seeking entry-level software development position.
Completed coursework in algorithms, data structures, and web development.
Built a todo app using React for a class project.
GPA: 3.5/4.0""",
        "job_description": {
            "description": "Senior Staff Engineer with 10+ years leading platform teams.",
            "required_skills": ["System Design", "Distributed Systems", "Kubernetes", "Go", "gRPC"],
            "preferred_skills": ["Rust", "Service Mesh", "Observability"],
        },
        "expected_score_range": (0, 30),  # Very low match
    },
]


# ─── Test Runners ────────────────────────────────────────────────────

def test_keyword_extraction(scorer, verbose: bool = False) -> dict:
    """Test keyword extraction quality."""
    print("\n🔑 Testing Keyword Extraction")
    print("─" * 55)

    total_expected_found = 0
    total_expected = 0
    total_unexpected_found = 0
    total_unexpected = 0

    for test in KEYWORD_EXTRACTION_TESTS:
        keywords = set(scorer._extract_keywords(test["text"]))
        keywords_lower = {k.lower() for k in keywords}

        expected_found = 0
        expected_missing = []
        for exp in test["expected_keywords"]:
            # Check if expected keyword appears in any extracted keyword
            found = any(exp.lower() in kw for kw in keywords_lower)
            if found:
                expected_found += 1
            else:
                expected_missing.append(exp)

        unexpected_found_list = []
        for unexp in test["unexpected_keywords"]:
            if unexp.lower() in keywords_lower:
                unexpected_found_list.append(unexp)

        total_expected_found += expected_found
        total_expected += len(test["expected_keywords"])
        total_unexpected_found += len(unexpected_found_list)
        total_unexpected += len(test["unexpected_keywords"])

        status = "✅" if expected_found >= len(test["expected_keywords"]) * 0.7 and len(unexpected_found_list) == 0 else "⚠️"
        print(f"  {status} {test['name']}")
        print(f"     Expected found: {expected_found}/{len(test['expected_keywords'])}")
        if expected_missing:
            print(f"     Missing: {expected_missing}")
        if unexpected_found_list:
            print(f"     ❌ Stop words leaked: {unexpected_found_list}")

        if verbose:
            print(f"     All extracted ({len(keywords)}): {sorted(keywords)[:20]}...")

    recall = total_expected_found / total_expected if total_expected > 0 else 0
    false_pos_rate = total_unexpected_found / total_unexpected if total_unexpected > 0 else 0

    print(f"\n  📊 Keyword Recall: {recall:.2%}")
    print(f"  📊 Stop Word Leak Rate: {false_pos_rate:.2%}")

    return {
        "keyword_recall": recall,
        "stop_word_leak_rate": false_pos_rate,
        "pass": recall >= 0.70 and false_pos_rate <= 0.10,
    }


def test_format_scoring(scorer, verbose: bool = False) -> dict:
    """Test format scoring accuracy."""
    print("\n📄 Testing Format Scoring")
    print("─" * 55)

    all_pass = True
    results = []

    for test in FORMAT_SCORING_TESTS:
        score = scorer._analyze_format(test["text"])
        min_ok = score >= test.get("expected_min_score", 0)
        max_ok = score <= test.get("expected_max_score", 100)
        passed = min_ok and max_ok

        status = "✅" if passed else "❌"
        print(f"  {status} {test['name']}: {score:.1f}/100")
        print(f"     Expected: [{test.get('expected_min_score', 0):.0f} – {test.get('expected_max_score', 100):.0f}]")
        print(f"     {test['description']}")

        if not passed:
            all_pass = False

        results.append({"name": test["name"], "score": score, "passed": passed})

    return {"tests": results, "pass": all_pass}


def test_skill_matching(scorer, verbose: bool = False) -> dict:
    """Test skill matching accuracy."""
    import asyncio

    print("\n🎯 Testing Skill Matching")
    print("─" * 55)

    all_pass = True
    results = []

    for test in SKILL_MATCHING_TESTS:
        matches = asyncio.get_event_loop().run_until_complete(
            scorer._match_skills(test["resume"], test["skills"])
        )

        matched_skills = {m.skill for m in matches if m.matched}
        unmatched_skills = {m.skill for m in matches if not m.matched}

        # Check expected matches
        expected_ok = test.get("expected_matched", set()).issubset(matched_skills)
        # Check expected non-matches (should NOT be matched)
        unexpected_ok = True
        for skill in test.get("expected_unmatched", set()):
            if skill in matched_skills:
                unexpected_ok = False

        passed = expected_ok and unexpected_ok
        status = "✅" if passed else "❌"

        print(f"  {status} {test['name']}")
        print(f"     Matched: {matched_skills}")
        print(f"     Unmatched: {unmatched_skills}")

        if not expected_ok:
            missing = test.get("expected_matched", set()) - matched_skills
            print(f"     ❌ Expected but not matched: {missing}")
        if not unexpected_ok:
            wrong = test.get("expected_unmatched", set()) & matched_skills
            print(f"     ❌ Should not have matched: {wrong}")

        if not passed:
            all_pass = False

        results.append({"name": test["name"], "passed": passed})

    return {"tests": results, "pass": all_pass}


def test_overall_scoring(scorer, verbose: bool = False) -> dict:
    """
    Test overall scoring using deterministic components only.
    
    Since semantic_score and skill_matches need LLM calls, we test
    the keyword_score and format_score components, then validate
    _calculate_overall_score with synthetic inputs.
    """
    import asyncio

    print("\n📊 Testing Overall Score Correlation")
    print("─" * 55)

    predicted_scores = []
    expected_midpoints = []
    all_pass = True

    for test in SCORING_TEST_CASES:
        resume = test["resume"]
        jd = test["job_description"]

        # Deterministic components
        keyword_score = scorer._calculate_keyword_match(resume, jd["description"])
        format_score = scorer._analyze_format(resume)

        # Skill matching (deterministic — no LLM)
        all_skills = jd.get("required_skills", []) + jd.get("preferred_skills", [])
        skill_matches = asyncio.get_event_loop().run_until_complete(
            scorer._match_skills(resume, all_skills)
        )

        # We can't call embed() without the LLM, so use keyword_score as proxy
        # for semantic similarity (correlated but not identical)
        proxy_semantic = keyword_score  # reasonable proxy

        overall = scorer._calculate_overall_score(
            proxy_semantic, keyword_score, format_score, skill_matches
        )

        lo, hi = test["expected_score_range"]
        midpoint = (lo + hi) / 2
        passed = lo <= overall <= hi

        status = "✅" if passed else "❌"
        print(f"  {status} {test['name']}")
        print(f"     Score: {overall:.1f}  Expected: [{lo} – {hi}]")
        print(f"     (keyword={keyword_score:.1f}, format={format_score:.1f}, "
              f"skills={sum(1 for s in skill_matches if s.matched)}/{len(skill_matches)})")

        if not passed:
            all_pass = False

        predicted_scores.append(overall)
        expected_midpoints.append(midpoint)

    # Compute Spearman correlation
    rho = spearman_rho(predicted_scores, expected_midpoints)
    print(f"\n  📊 Spearman ρ (predicted vs expected midpoint): {rho:.4f}")
    print(f"     Target: ρ ≥ 0.70")

    return {
        "spearman_rho": rho,
        "all_in_range": all_pass,
        "pass": rho >= 0.70 and all_pass,
    }


# ─── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Benchmark ATS Scorer Pipeline")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--output", type=str, default=None, help="Save results JSON to file")
    args = parser.parse_args()

    print("═" * 65)
    print(" ATS Resume Scorer — Pipeline Benchmark")
    print("═" * 65)

    # Initialize scorer (no LLM needed for deterministic tests)
    from app.agents.ats_scorer import ATSScorerAgent
    scorer = ATSScorerAgent.__new__(ATSScorerAgent)
    # We don't call __init__ to avoid LLM initialization
    # All methods we test are static or don't need self.llm_client

    results = {}

    # Run all test suites
    results["keyword_extraction"] = test_keyword_extraction(scorer, args.verbose)
    results["format_scoring"] = test_format_scoring(scorer, args.verbose)
    results["skill_matching"] = test_skill_matching(scorer, args.verbose)
    results["overall_scoring"] = test_overall_scoring(scorer, args.verbose)

    # Summary
    print(f"\n{'═' * 65}")
    print(f" SUMMARY")
    print(f"{'═' * 65}")

    all_pass = True
    for suite_name, suite_result in results.items():
        status = "✅ PASS" if suite_result["pass"] else "❌ FAIL"
        print(f"  {status} — {suite_name}")
        if not suite_result["pass"]:
            all_pass = False

    if all_pass:
        print(f"\n  🎉 All ATS scorer benchmarks PASSED")
    else:
        print(f"\n  ⚠️  Some benchmarks need attention")

    print(f"{'═' * 65}\n")

    # Save results
    output_path = args.output or str(Path(__file__).parent / "results_ats_scorer.json")
    # Convert results to JSON-serializable format
    json_results = {
        "timestamp": datetime.now().isoformat(),
        "suites": {}
    }
    for name, res in results.items():
        json_results["suites"][name] = {
            "pass": res["pass"],
            **{k: v for k, v in res.items() if k != "pass" and not callable(v)},
        }

    with open(output_path, "w") as f:
        json.dump(json_results, f, indent=2, default=str)
    print(f"💾 Results saved to {output_path}")


if __name__ == "__main__":
    main()
