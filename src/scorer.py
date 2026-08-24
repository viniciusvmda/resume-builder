"""TF-IDF and keyword-based scoring engine for ATS optimization."""

import re

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models import (
    Certification,
    Experience,
    ExperienceBullet,
    ResumeData,
    Skill,
)

# Common stop words to exclude from keyword extraction
STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "shall",
    "can",
    "need",
    "must",
    "that",
    "this",
    "these",
    "those",
    "it",
    "its",
    "we",
    "you",
    "they",
    "our",
    "your",
    "their",
    "my",
    "his",
    "her",
    "who",
    "what",
    "which",
    "when",
    "where",
    "how",
    "all",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "not",
    "only",
    "same",
    "so",
    "than",
    "too",
    "very",
    "just",
    "about",
    "above",
    "after",
    "again",
    "also",
    "as",
    "because",
    "before",
    "between",
    "during",
    "if",
    "into",
    "through",
    "under",
    "until",
    "up",
    "while",
    "able",
    "work",
    "working",
    "experience",
    "including",
    "using",
    "well",
    "strong",
    "required",
    "preferred",
    "etc",
    "team",
    "teams",
    "role",
    "ability",
    "across",
}


def extract_keywords(text: str, top_n: int = 50) -> list[str]:
    """Extract top keywords from text using TF-IDF on sentences."""
    sentences = re.split(r"[.\n•\-;,]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]

    if not sentences:
        return []

    vectorizer = TfidfVectorizer(
        stop_words=list(STOP_WORDS),
        ngram_range=(1, 3),
        max_features=200,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9.#+/\-]{1,}\b",
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(sentences)
    except ValueError:
        return []

    feature_names = vectorizer.get_feature_names_out()
    scores = tfidf_matrix.sum(axis=0).A1
    scored_terms = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)

    return [term for term, _ in scored_terms[:top_n]]


def score_text_similarity(text: str, job_description: str) -> float:
    """Score a text's similarity to a job description using TF-IDF cosine similarity."""
    if not text.strip() or not job_description.strip():
        return 0.0

    vectorizer = TfidfVectorizer(
        stop_words=list(STOP_WORDS),
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9.#+/\-]{1,}\b",
    )

    try:
        tfidf_matrix = vectorizer.fit_transform([job_description, text])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except ValueError:
        return 0.0


def score_keyword_match(text: str, keywords: list[str]) -> float:
    """Score text based on exact and fuzzy keyword presence."""
    if not keywords:
        return 0.0

    text_lower = text.lower()
    matches = 0

    for keyword in keywords:
        kw_lower = keyword.lower()
        # Exact match
        if kw_lower in text_lower:
            matches += 1.0
        else:
            # Fuzzy match (partial ratio for substring matching)
            ratio = fuzz.partial_ratio(kw_lower, text_lower)
            if ratio >= 85:
                matches += ratio / 100.0

    return matches / len(keywords)


def score_skill(skill: Skill, jd_keywords: list[str], job_description: str) -> float:
    """Score a single skill against job description keywords."""
    all_names = [skill.name] + skill.aliases
    best_score = 0.0

    for name in all_names:
        name_lower = name.lower()
        # Check exact presence in JD
        if name_lower in job_description.lower():
            best_score = max(best_score, 1.0)
            break

        # Check against extracted keywords
        for kw in jd_keywords:
            if name_lower == kw.lower():
                best_score = max(best_score, 1.0)
                break
            ratio = fuzz.ratio(name_lower, kw.lower())
            if ratio >= 85:
                best_score = max(best_score, ratio / 100.0)

    # Boost by years of experience (normalized)
    years_boost = min((skill.years or 0) / 10.0, 0.3)
    return best_score + years_boost


def score_bullet(
    bullet: ExperienceBullet, jd_keywords: list[str], job_description: str
) -> float:
    """Score a single experience bullet against the job description."""
    tfidf_score = score_text_similarity(bullet.text, job_description)
    keyword_score = score_keyword_match(bullet.text, jd_keywords)

    return (tfidf_score * 0.4) + (keyword_score * 0.5)


def score_experience(
    experience: Experience, jd_keywords: list[str], job_description: str
) -> float:
    """Score an entire experience entry."""
    # Score role title match
    role_score = score_keyword_match(experience.role, jd_keywords)

    # Score description if present
    desc_score = 0.0
    if experience.description:
        desc_score = score_text_similarity(experience.description, job_description)

    # Average bullet scores
    bullet_scores = [
        score_bullet(b, jd_keywords, job_description) for b in experience.bullets
    ]
    avg_bullet_score = sum(bullet_scores) / len(bullet_scores) if bullet_scores else 0.0

    # Bonus for the role's own keywords appearing in the job description
    keyword_bonus = 0.0
    if experience.keywords:
        overlap = sum(
            1 for kw in experience.keywords if kw.lower() in job_description.lower()
        )
        keyword_bonus = overlap / len(experience.keywords) * 0.2

    return (
        (role_score * 0.3)
        + (desc_score * 0.2)
        + (avg_bullet_score * 0.5)
        + keyword_bonus
    )


def score_certification(
    cert: Certification, jd_keywords: list[str], job_description: str
) -> float:
    """Score a certification against the job description."""
    return score_keyword_match(cert.name, jd_keywords)


def score_resume(resume_data: ResumeData, job_description: str) -> dict:
    """Score all resume components against a job description.

    Returns a dict with scored items for use by the selector.
    """
    jd_keywords = extract_keywords(job_description)

    # Score skills
    scored_skills: list[tuple[str, Skill, float]] = []
    for category in resume_data.skill_categories:
        for skill in category.skills:
            s = score_skill(skill, jd_keywords, job_description)
            scored_skills.append((category.category, skill, s))

    # Score experiences
    scored_experiences: list[
        tuple[Experience, float, list[tuple[ExperienceBullet, float]]]
    ] = []
    for exp in resume_data.experiences:
        exp_score = score_experience(exp, jd_keywords, job_description)
        bullet_scores = [
            (b, score_bullet(b, jd_keywords, job_description)) for b in exp.bullets
        ]
        scored_experiences.append((exp, exp_score, bullet_scores))

    # Score certifications
    scored_certs = [
        (c, score_certification(c, jd_keywords, job_description))
        for c in resume_data.certifications
    ]

    # Compute overall match score
    all_scores = (
        [s for _, _, s in scored_skills]
        + [s for _, s, _ in scored_experiences]
        + [s for _, s in scored_certs]
    )
    overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

    return {
        "jd_keywords": jd_keywords,
        "scored_skills": scored_skills,
        "scored_experiences": scored_experiences,
        "scored_certifications": scored_certs,
        "overall_score": overall_score,
    }
