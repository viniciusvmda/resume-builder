"""TF-IDF and keyword-based scoring engine for ATS optimization."""

import re
from typing import NamedTuple

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

# Common stop words to exclude from keyword extraction.
# NOTE: "no"/"not" and "required"/"preferred" are intentionally NOT here —
# they carry signal (negation, hard-requirement vs nice-to-have) that the
# scorer relies on. See NEGATION_CUES and CUE_PHRASES below.
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
    "etc",
    "team",
    "teams",
    "role",
    "ability",
    "across",
}

# Token pattern shared by every TfidfVectorizer instance. Allows 1-character
# terms (e.g. "C", "R") which the original 2+-char pattern silently dropped.
TOKEN_PATTERN = r"(?u)\b[a-zA-Z][a-zA-Z0-9.#+/\-]*\b"

# Cue phrases used to classify JD keywords as hard requirements vs nice-to-haves.
CUE_PHRASES = {
    "required": ("required", "must have", "must-have"),
    "preferred": ("preferred", "nice to have", "nice-to-have", "bonus", "plus"),
}

# Negation cues checked in the tokens preceding a keyword match.
NEGATION_CUES = {"no", "not", "without", "former", "legacy", "lack"}
NEGATION_WINDOW = 6

# Weights applied to keyword matches depending on required/preferred classification.
REQUIRED_WEIGHT = 1.0
PREFERRED_WEIGHT = 0.6
GENERAL_WEIGHT = 0.4

# Weights for the final weighted overall_score formula.
OVERALL_SCORE_WEIGHTS = {
    "skills": 0.35,
    "experience": 0.40,
    "certifications": 0.10,
    "keyword_coverage": 0.15,
}


class MatchDetail(NamedTuple):
    keyword: str
    match_type: str  # "exact", "fuzzy", "negated", "missing"
    score: float


class YearsRequirement(NamedTuple):
    skill_hint: str
    min_years: float
    max_years: float | None


def _preceding_tokens(text_lower: str, match_start: int, window: int = NEGATION_WINDOW) -> list[str]:
    """Return up to `window` word tokens immediately before `match_start`."""
    before = text_lower[:match_start]
    tokens = re.findall(r"[a-z0-9']+", before)
    return tokens[-window:]


def is_negated(preceding_tokens: list[str]) -> bool:
    """Whether any negation cue appears in the given preceding tokens."""
    return any(tok in NEGATION_CUES for tok in preceding_tokens)


def fuzzy_match_ok(a: str, b: str, use_partial: bool = False) -> tuple[bool, float]:
    """Length-aware fuzzy match between two lowercased strings.

    Fuzzy matching is disabled for very short strings (<=3 chars), where
    edit-distance percentages are not meaningful and produce false positives.
    Shorter strings (4-6 chars) require a stricter threshold than longer ones.
    """
    min_len = min(len(a), len(b))
    if min_len <= 3:
        return (True, 1.0) if a == b else (False, 0.0)

    threshold = 92 if min_len <= 6 else 85
    ratio = fuzz.partial_ratio(a, b) if use_partial else fuzz.ratio(a, b)
    if ratio >= threshold:
        return True, ratio / 100.0
    return False, 0.0


def _prepare_keyword_source_text(text: str) -> str:
    """Drop section-header lines ("Requirements:", "Nice to have:", ...) and
    rejoin line-wrapped bullet continuations into one logical line each.

    Without this, header words dominate the TF-IDF ranking (they sit alone on
    their own short line, which TfidfVectorizer L2-normalizes to a maxed-out
    weight), and a bullet wrapped across two physical lines gets fragmented
    into two artificially short "documents" instead of one coherent sentence.
    """
    logical_lines: list[str] = []
    current = ""

    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            if current:
                logical_lines.append(current)
                current = ""
            continue

        if (
            _HEADER_REQUIRED_RE.match(stripped)
            or _HEADER_PREFERRED_RE.match(stripped)
            or _HEADER_GENERIC_RE.match(stripped)
        ):
            if current:
                logical_lines.append(current)
                current = ""
            continue

        if _BULLET_PREFIX_RE.match(stripped):
            if current:
                logical_lines.append(current)
            current = _BULLET_PREFIX_RE.sub("", stripped)
        else:
            current = f"{current} {stripped}".strip()

    if current:
        logical_lines.append(current)

    return "\n".join(logical_lines)


def extract_keywords(text: str, top_n: int = 50) -> list[str]:
    """Extract top keywords from text using TF-IDF on sentences."""
    # Split only on real sentence/line boundaries. Splitting on comma or
    # hyphen (as an earlier version did) shreds comma-separated skill lists
    # ("Go, Java, or Python") and hyphenated terms ("on-call") into isolated
    # single-word fragments; since each fragment is its own TF-IDF document
    # (L2-normalized), an accidentally-isolated word gets an inflated score
    # while genuinely important terms sharing a list get diluted.
    prepared = _prepare_keyword_source_text(text)
    sentences = re.split(r"[.\n•;]", prepared)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]

    if not sentences:
        return []

    vectorizer = TfidfVectorizer(
        stop_words=list(STOP_WORDS),
        ngram_range=(1, 2),
        max_features=200,
        token_pattern=TOKEN_PATTERN,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(sentences)
    except ValueError:
        return []

    feature_names = vectorizer.get_feature_names_out()
    # Rank by each term's best single-sentence weight, not summed across all
    # sentences. Summing systematically favors generic words repeated across
    # many short sentences (e.g. "backend", "platform") over specific
    # technologies that a JD typically names exactly once each in a
    # requirements list (e.g. "kafka", "postgresql").
    scores = tfidf_matrix.max(axis=0).toarray().flatten()
    scored_terms = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)

    return [term for term, _ in scored_terms[:top_n]]


_HEADER_REQUIRED_RE = re.compile(
    r"^(requirements?|must[\s-]?haves?|qualifications)\s*:?\s*$", re.IGNORECASE
)
_HEADER_PREFERRED_RE = re.compile(
    r"^(nice[\s-]?to[\s-]?haves?|preferred(\s+qualifications)?|bonus(es)?|good[\s-]?to[\s-]?haves?)\s*:?\s*$",
    re.IGNORECASE,
)
# Any other short "Title:" line resets classification back to general
# (e.g. "Responsibilities:", "About the role:").
_HEADER_GENERIC_RE = re.compile(r"^[A-Za-z][A-Za-z /]{0,40}:\s*$")
_BULLET_PREFIX_RE = re.compile(r"^[-•*]\s*")


def classify_jd_keywords(job_description: str, keywords: list[str]) -> dict[str, set[str]]:
    """Classify JD keywords as required / preferred / general.

    Two signals are combined: an inline cue phrase in the same sentence
    ("Python is required") and a section header that most real job postings
    use instead ("Requirements:" followed by a bulleted list, until the next
    header). The inline cue always wins when present on a line.
    """
    keywords_lower = {kw.lower(): kw for kw in keywords}
    required: set[str] = set()
    preferred: set[str] = set()
    section_state = "general"

    for line in job_description.split("\n"):
        stripped = _BULLET_PREFIX_RE.sub("", line.strip()).strip()
        if not stripped:
            continue

        if _HEADER_REQUIRED_RE.match(stripped):
            section_state = "required"
            continue
        if _HEADER_PREFERRED_RE.match(stripped):
            section_state = "preferred"
            continue
        if _HEADER_GENERIC_RE.match(stripped):
            section_state = "general"
            continue

        for sentence in re.split(r"[.;]", stripped):
            sentence_lower = sentence.lower().strip()
            if not sentence_lower:
                continue
            is_required = any(cue in sentence_lower for cue in CUE_PHRASES["required"])
            is_preferred = any(cue in sentence_lower for cue in CUE_PHRASES["preferred"])
            if is_required:
                effective_state = "required"
            elif is_preferred:
                effective_state = "preferred"
            else:
                effective_state = section_state

            if effective_state == "general":
                continue
            for kw_lower, kw in keywords_lower.items():
                if kw_lower not in sentence_lower:
                    continue
                (required if effective_state == "required" else preferred).add(kw)

    general = set(keywords) - required - preferred
    return {"required": required, "preferred": preferred, "general": general}


def _keyword_weight(kw_lower: str, jd_classification: dict[str, set[str]] | None) -> float:
    if not jd_classification:
        return 1.0
    required = {k.lower() for k in jd_classification.get("required", set())}
    preferred = {k.lower() for k in jd_classification.get("preferred", set())}
    if kw_lower in required:
        return REQUIRED_WEIGHT
    if kw_lower in preferred:
        return PREFERRED_WEIGHT
    return GENERAL_WEIGHT


_YEARS_FILLER = {"of", "in", "with", "and", "the", "years", "year", "experience", "a", "as"}
_YEARS_PATTERN = re.compile(r"(\d+)(?:\s*-\s*(\d+))?\+?\s*years?", re.IGNORECASE)
_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+#./\-]*")
_SENTENCE_BOUNDARY = re.compile(r"[.\n•;]")


def extract_years_requirements(job_description: str) -> list[YearsRequirement]:
    """Extract simple "X+ years [of] <skill>" / "X-Y years <skill>" requirements.

    This is a lightweight heuristic (nearest keyword-like words around the
    match, clipped to the enclosing sentence), not full NLP — it will miss
    requirements phrased unusually.
    """
    requirements: list[YearsRequirement] = []

    for m in _YEARS_PATTERN.finditer(job_description):
        min_years = float(m.group(1))
        max_years = float(m.group(2)) if m.group(2) else None

        # Clip the search window to the current sentence so a requirement
        # doesn't bleed its "years" into an unrelated skill mentioned next.
        next_boundary = _SENTENCE_BOUNDARY.search(job_description, m.end())
        after_end = next_boundary.start() if next_boundary else min(len(job_description), m.end() + 60)
        after = job_description[m.end() : after_end]
        after_words = _WORD_PATTERN.findall(after)
        hint_words = [w for w in after_words if w.lower() not in _YEARS_FILLER][:3]

        if not hint_words:
            prev_boundaries = list(_SENTENCE_BOUNDARY.finditer(job_description, 0, m.start()))
            before_start = prev_boundaries[-1].end() if prev_boundaries else max(0, m.start() - 40)
            before = job_description[before_start : m.start()]
            before_words = _WORD_PATTERN.findall(before)
            hint_words = [w for w in before_words if w.lower() not in _YEARS_FILLER][-3:]

        if hint_words:
            requirements.append(YearsRequirement(" ".join(hint_words), min_years, max_years))

    return requirements


def score_years_requirement(skill: Skill, requirements: list[YearsRequirement] | None) -> float:
    """Multiplier in [0,1] penalizing a skill whose years fall short of a JD requirement.

    Returns 1.0 (neutral) when no requirement matches this skill.
    """
    if not requirements:
        return 1.0

    names = [skill.name.lower()] + [a.lower() for a in skill.aliases]
    for req in requirements:
        hint_lower = req.skill_hint.lower()
        matched = any(name in hint_lower or hint_lower in name for name in names)
        if not matched:
            matched = any(fuzzy_match_ok(name, hint_lower, use_partial=True)[0] for name in names)
        if not matched:
            continue

        if req.min_years <= 0:
            return 1.0
        if skill.years is None:
            return 0.0
        if skill.years >= req.min_years:
            return 1.0
        return max(skill.years / req.min_years, 0.0)

    return 1.0


def build_jd_vectorizer(job_description: str):
    """Fit one TF-IDF vectorizer on the JD, reused across all similarity checks
    in a single score_resume() call instead of refitting per bullet/description."""
    if not job_description.strip():
        return None, None

    vectorizer = TfidfVectorizer(
        stop_words=list(STOP_WORDS),
        ngram_range=(1, 2),
        token_pattern=TOKEN_PATTERN,
    )
    try:
        jd_vector = vectorizer.fit_transform([job_description])
    except ValueError:
        return None, None

    return vectorizer, jd_vector


def score_text_similarity(text: str, job_description: str) -> float:
    """Score a text's similarity to a job description using TF-IDF cosine similarity.

    Standalone convenience wrapper that fits its own throwaway vectorizer.
    Internal callers within score_resume() use score_text_similarity_cached
    instead to avoid refitting a vectorizer per call.
    """
    if not text.strip() or not job_description.strip():
        return 0.0

    vectorizer = TfidfVectorizer(
        stop_words=list(STOP_WORDS),
        ngram_range=(1, 2),
        token_pattern=TOKEN_PATTERN,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform([job_description, text])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except ValueError:
        return 0.0


def score_text_similarity_cached(text: str, jd_vector, vectorizer) -> float:
    """Score text similarity against a pre-fitted JD vectorizer/vector (see
    build_jd_vectorizer). Falls back to 0.0 if the JD couldn't be vectorized."""
    if not text.strip() or vectorizer is None or jd_vector is None:
        return 0.0
    try:
        text_vector = vectorizer.transform([text])
    except ValueError:
        return 0.0
    similarity = cosine_similarity(jd_vector, text_vector)[0][0]
    return float(similarity)


def _match_keywords(
    text: str, keywords: list[str], jd_classification: dict[str, set[str]] | None = None
) -> list[MatchDetail]:
    text_lower = text.lower()
    details: list[MatchDetail] = []

    for keyword in keywords:
        kw_lower = keyword.lower()
        idx = text_lower.find(kw_lower)
        if idx != -1:
            if is_negated(_preceding_tokens(text_lower, idx)):
                details.append(MatchDetail(keyword, "negated", 0.0))
            else:
                details.append(MatchDetail(keyword, "exact", 1.0))
            continue

        matched, score = fuzzy_match_ok(kw_lower, text_lower, use_partial=True)
        if matched:
            details.append(MatchDetail(keyword, "fuzzy", score))
        else:
            details.append(MatchDetail(keyword, "missing", 0.0))

    return details


def score_keyword_match(
    text: str, keywords: list[str], jd_classification: dict[str, set[str]] | None = None
) -> float:
    """Score text based on exact and fuzzy keyword presence, weighted by
    required/preferred classification when provided. Always returns [0, 1]."""
    if not keywords:
        return 0.0

    details = _match_keywords(text, keywords, jd_classification)
    weighted_matches = 0.0
    weighted_total = 0.0
    for d in details:
        weight = _keyword_weight(d.keyword.lower(), jd_classification)
        weighted_total += weight
        weighted_matches += d.score * weight

    return weighted_matches / weighted_total if weighted_total else 0.0


def score_keyword_match_detailed(
    text: str, keywords: list[str], jd_classification: dict[str, set[str]] | None = None
) -> list[MatchDetail]:
    """Like score_keyword_match, but returns per-keyword match detail for explainability."""
    return _match_keywords(text, keywords, jd_classification)


def score_skill(
    skill: Skill,
    jd_keywords: list[str],
    job_description: str,
    years_requirements: list[YearsRequirement] | None = None,
) -> float:
    """Score a single skill against job description keywords. Always returns [0, 1]."""
    all_names = [skill.name] + skill.aliases
    jd_lower = job_description.lower()
    best_score = 0.0

    for name in all_names:
        name_lower = name.lower()
        idx = jd_lower.find(name_lower)
        if idx != -1:
            if not is_negated(_preceding_tokens(jd_lower, idx)):
                best_score = 1.0
            break

        for kw in jd_keywords:
            kw_lower = kw.lower()
            if name_lower == kw_lower:
                best_score = max(best_score, 1.0)
                break
            matched, score = fuzzy_match_ok(name_lower, kw_lower)
            if matched:
                best_score = max(best_score, score)

        if best_score >= 1.0:
            break

    years_multiplier = (
        score_years_requirement(skill, years_requirements) if years_requirements else 1.0
    )
    return min(best_score * years_multiplier, 1.0)


# Weighted-match-units a single item (bullet/role/cert) needs to hit full
# score. E.g. 2-3 required-weight (1.0) keyword hits, or a proportionally
# larger number of lower-weight ones, saturates to 1.0.
ITEM_SATURATION = 2.5


def score_keyword_relevance(
    text: str,
    keywords: list[str],
    jd_classification: dict[str, set[str]] | None = None,
    saturation: float = ITEM_SATURATION,
) -> float:
    """Score how strongly `text` matches JD keywords via a capped weighted
    sum, not a ratio.

    score_keyword_match (matched weight / total weight of the given keyword
    list) is a recall metric: appropriate when the text is large enough to
    plausibly cover a real fraction of the keyword list (e.g. the whole
    resume, for keyword_coverage). Applied to a single short item (a bullet,
    a role title, a cert name) against a large keyword list, that ratio is
    structurally capped low regardless of match quality — and scoping the
    list to the item itself just moves the unfairness to comparisons between
    items with different footprints (a narrow/generic item's smaller
    denominator makes it easier to satisfy than a broad/specific one).

    This function has no such denominator: unmatched keywords simply don't
    contribute. Every item is compared on the same fixed scale, so an item
    that hits more/higher-value keywords always scores at least as well as
    one that hits fewer, regardless of either item's own keyword footprint.
    """
    if not keywords or saturation <= 0:
        return 0.0
    details = _match_keywords(text, keywords, jd_classification)
    matched_weight = sum(
        _keyword_weight(d.keyword.lower(), jd_classification) * d.score
        for d in details
        if d.match_type in ("exact", "fuzzy")
    )
    return min(matched_weight / saturation, 1.0)


def score_bullet(
    bullet: ExperienceBullet,
    jd_keywords: list[str],
    job_description: str,
    jd_vector=None,
    vectorizer=None,
    jd_classification: dict[str, set[str]] | None = None,
) -> float:
    """Score a single experience bullet against the job description. Weights sum to 1.0."""
    if jd_vector is not None and vectorizer is not None:
        tfidf_score = score_text_similarity_cached(bullet.text, jd_vector, vectorizer)
    else:
        tfidf_score = score_text_similarity(bullet.text, job_description)
    keyword_score = score_keyword_relevance(bullet.text, jd_keywords, jd_classification)

    return (tfidf_score * 0.4) + (keyword_score * 0.6)


def _score_experience_detailed(
    experience: Experience,
    jd_keywords: list[str],
    job_description: str,
    jd_vector=None,
    vectorizer=None,
    jd_classification: dict[str, set[str]] | None = None,
) -> tuple[float, list[tuple[ExperienceBullet, float]]]:
    """Score an experience entry, returning both its scalar score and the
    per-bullet scores computed along the way (avoids re-scoring bullets twice)."""
    role_score = score_keyword_relevance(experience.role, jd_keywords, jd_classification)

    desc_score = 0.0
    if experience.description:
        if jd_vector is not None and vectorizer is not None:
            desc_score = score_text_similarity_cached(experience.description, jd_vector, vectorizer)
        else:
            desc_score = score_text_similarity(experience.description, job_description)

    bullet_scores = [
        (b, score_bullet(b, jd_keywords, job_description, jd_vector, vectorizer, jd_classification))
        for b in experience.bullets
    ]
    avg_bullet_score = (
        sum(s for _, s in bullet_scores) / len(bullet_scores) if bullet_scores else 0.0
    )

    keyword_bonus = 0.0
    if experience.keywords:
        overlap = sum(
            1 for kw in experience.keywords if kw.lower() in job_description.lower()
        )
        keyword_bonus = overlap / len(experience.keywords)

    # Weights sum to 1.0 by construction, plus a defense-in-depth clamp.
    score = min(
        (role_score * 0.3) + (desc_score * 0.2) + (avg_bullet_score * 0.4) + (keyword_bonus * 0.1),
        1.0,
    )
    return score, bullet_scores


def score_experience(
    experience: Experience, jd_keywords: list[str], job_description: str
) -> float:
    """Score an entire experience entry. Always returns [0, 1]."""
    score, _ = _score_experience_detailed(experience, jd_keywords, job_description)
    return score


def score_certification(
    cert: Certification,
    jd_keywords: list[str],
    job_description: str,
    jd_classification: dict[str, set[str]] | None = None,
) -> float:
    """Score a certification against the job description. Always returns [0, 1]."""
    return score_keyword_relevance(cert.name, jd_keywords, jd_classification)


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _all_resume_text(resume_data: ResumeData) -> str:
    parts = [resume_data.profile.headline, resume_data.profile.summary]
    for exp in resume_data.experiences:
        parts.append(exp.role)
        parts.append(exp.description or "")
        parts.extend(b.text for b in exp.bullets)
    for category in resume_data.skill_categories:
        for skill in category.skills:
            parts.append(skill.name)
            parts.extend(skill.aliases)
    for cert in resume_data.certifications:
        parts.append(cert.name)
    return " ".join(p for p in parts if p)


def score_resume(resume_data: ResumeData, job_description: str) -> dict:
    """Score all resume components against a job description.

    Returns a dict with scored items for use by the selector, a categorical
    breakdown, and an explanation of what drove (or hurt) the overall score.
    """
    jd_keywords = extract_keywords(job_description)
    jd_classification = classify_jd_keywords(job_description, jd_keywords)
    years_requirements = extract_years_requirements(job_description)
    vectorizer, jd_vector = build_jd_vectorizer(job_description)

    # Score skills
    scored_skills: list[tuple[str, Skill, float]] = []
    for category in resume_data.skill_categories:
        for skill in category.skills:
            s = score_skill(skill, jd_keywords, job_description, years_requirements)
            scored_skills.append((category.category, skill, s))

    # Score experiences (bullet scores computed once here, reused for both
    # the experience's own average and the per-bullet detail returned below)
    scored_experiences: list[
        tuple[Experience, float, list[tuple[ExperienceBullet, float]]]
    ] = []
    for exp in resume_data.experiences:
        exp_score, bullet_scores = _score_experience_detailed(
            exp, jd_keywords, job_description, jd_vector, vectorizer, jd_classification
        )
        scored_experiences.append((exp, exp_score, bullet_scores))

    # Score certifications
    scored_certs = [
        (c, score_certification(c, jd_keywords, job_description, jd_classification))
        for c in resume_data.certifications
    ]

    all_resume_text = _all_resume_text(resume_data)
    required_keywords = list(jd_classification["required"])
    if required_keywords:
        keyword_coverage = score_keyword_match(all_resume_text, required_keywords)
    else:
        keyword_coverage = score_keyword_match(all_resume_text, jd_keywords, jd_classification)

    category_scores = {
        "skills": _mean(s for _, _, s in scored_skills),
        "experience": _mean(s for _, s, _ in scored_experiences),
        "certifications": _mean(s for _, s in scored_certs),
        "keyword_coverage": keyword_coverage,
    }

    overall_score = sum(
        category_scores[key] * weight for key, weight in OVERALL_SCORE_WEIGHTS.items()
    )

    keyword_details = score_keyword_match_detailed(all_resume_text, jd_keywords, jd_classification)
    required_lower = {k.lower() for k in jd_classification["required"]}
    preferred_lower = {k.lower() for k in jd_classification["preferred"]}
    explanation = {
        "matched_required": [
            d.keyword
            for d in keyword_details
            if d.match_type in ("exact", "fuzzy") and d.keyword.lower() in required_lower
        ],
        "matched_preferred": [
            d.keyword
            for d in keyword_details
            if d.match_type in ("exact", "fuzzy") and d.keyword.lower() in preferred_lower
        ],
        "missing_required": [
            d.keyword
            for d in keyword_details
            if d.match_type == "missing" and d.keyword.lower() in required_lower
        ],
        "missing_preferred": [
            d.keyword
            for d in keyword_details
            if d.match_type == "missing" and d.keyword.lower() in preferred_lower
        ],
        "negated_matches_discounted": [
            d.keyword for d in keyword_details if d.match_type == "negated"
        ],
    }

    return {
        "jd_keywords": jd_keywords,
        "jd_requirements": {
            "required": jd_classification["required"],
            "preferred": jd_classification["preferred"],
            "years_requirements": years_requirements,
        },
        "scored_skills": scored_skills,
        "scored_experiences": scored_experiences,
        "scored_certifications": scored_certs,
        "category_scores": category_scores,
        "overall_score": overall_score,
        "explanation": explanation,
    }
