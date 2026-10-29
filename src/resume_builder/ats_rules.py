"""ATS formatting rules and constants."""

# Standard section headings by language
SECTION_HEADINGS_EN = {
    "summary": "Professional Summary",
    "education": "Education",
    "experience": "Professional Experience",
    "projects": "Projects",
    "skills": "Technical Skills",
    "certifications": "Certifications",
    "languages": "Languages",
}

SECTION_HEADINGS_PT = {
    "summary": "Resumo Profissional",
    "education": "Formação Acadêmica",
    "experience": "Experiência Profissional",
    "projects": "Projetos",
    "skills": "Habilidades Técnicas",
    "certifications": "Certificações",
    "languages": "Idiomas",
}

SECTION_HEADINGS_BY_LANG = {
    "en": SECTION_HEADINGS_EN,
    "pt-br": SECTION_HEADINGS_PT,
    "pt": SECTION_HEADINGS_PT,
}

SECTION_HEADINGS = SECTION_HEADINGS_EN


def get_section_headings(lang: str = "en") -> dict[str, str]:
    """Get section headings dictionary for the specified language."""
    key = (lang or "en").lower().strip()
    return SECTION_HEADINGS_BY_LANG.get(key, SECTION_HEADINGS_EN)


# UI text labels by language
LABELS_EN = {
    "year": "year",
    "years": "years",
    "technologies_used": "Technologies used: ",
    "present": "Present",
}

LABELS_PT = {
    "year": "ano",
    "years": "anos",
    "technologies_used": "Tecnologias utilizadas: ",
    "present": "Atual",
}

LABELS_BY_LANG = {
    "en": LABELS_EN,
    "pt-br": LABELS_PT,
    "pt": LABELS_PT,
}


def get_labels(lang: str = "en") -> dict[str, str]:
    """Get text labels dictionary for the specified language."""
    key = (lang or "en").lower().strip()
    return LABELS_BY_LANG.get(key, LABELS_EN)

# Section order for generic resume (original upstream project default)
DEFAULT_SECTION_ORDER = [
    "summary",
    "experience",
    "projects",
    "certifications",
    "education",
    "skills",
]

# Mapping between YAML file names (or section aliases) and internal section keys
YAML_SECTION_MAP = {
    "profile": "summary",
    "summary": "summary",
    "experiences": "experience",
    "experience": "experience",
    "projects": "projects",
    "project": "projects",
    "skills": "skills",
    "skill": "skills",
    "certifications": "certifications",
    "certification": "certifications",
    "education": "education",
    "languages": "languages",
    "language": "languages",
}


def resolve_section_order(
    order: str | list[str] | None = None,
    available_languages: bool = False,
) -> list[str]:
    """Parse and normalize section order from YAML names or canonical section names.

    If order is None, returns the original default section order of the project.
    """
    if order is None:
        default_order = list(DEFAULT_SECTION_ORDER)
        if available_languages and "languages" not in default_order:
            idx = (
                default_order.index("education") + 1
                if "education" in default_order
                else len(default_order)
            )
            default_order.insert(idx, "languages")
        return default_order

    if isinstance(order, str):
        items = [s.strip() for s in order.split(",") if s.strip()]
    else:
        items = [str(s).strip() for s in order if str(s).strip()]

    resolved = []
    seen = set()
    for item in items:
        clean = item.lower()
        if clean.endswith(".yaml"):
            clean = clean[:-5]
        elif clean.endswith(".yml"):
            clean = clean[:-4]

        canonical = YAML_SECTION_MAP.get(clean)
        if not canonical:
            valid = ", ".join(sorted(set(YAML_SECTION_MAP.keys())))
            raise ValueError(
                f"Unknown section name '{item}'. Valid names (YAML names) are: {valid}"
            )

        if canonical not in seen:
            resolved.append(canonical)
            seen.add(canonical)

    return resolved

# PDF formatting constants
FONT_FAMILY = "Helvetica"

SUPPORTED_FONTS = {
    "helvetica": "Helvetica",
    "cmu": "CMU Serif Roman",
    "cmu-serif": "CMU Serif Roman",
    "cmu serif": "CMU Serif Roman",
    "cmu serif roman": "CMU Serif Roman",
    "times": "Times",
    "courier": "Courier",
}


def resolve_font_family(font: str | None = None) -> str:
    """Normalize font name to a supported font family, defaulting to Helvetica."""
    if not font:
        return FONT_FAMILY
    key = font.lower().strip()
    return SUPPORTED_FONTS.get(key, font.strip())
FONT_SIZE_NAME = 18
FONT_SIZE_HEADING = 12
FONT_SIZE_SUBHEADING = 10
FONT_SIZE_BODY = 9.5
FONT_SIZE_SMALL = 8.5

LINE_HEIGHT = 4.5
SECTION_SPACING = 6
BULLET_INDENT = 4

PAGE_MARGIN_LEFT = 15
PAGE_MARGIN_RIGHT = 15
PAGE_MARGIN_TOP = 15
PAGE_MARGIN_BOTTOM = 15

# Maximum bullets per experience entry (for page constraint)
MAX_BULLETS_PER_EXPERIENCE = 6
MAX_BULLETS_PER_EXPERIENCE_TARGETED = 5

# Maximum bullets per project entry (for page constraint)
MAX_BULLETS_PER_PROJECT = 4
MAX_BULLETS_PER_PROJECT_TARGETED = 3

# Maximum number of skills per category to show
MAX_SKILLS_PER_CATEGORY = 12

# Page constraints
MAX_PAGES = 2

# --- PDF text parsing (simulated-ATS scoring) ---
#
# Synonym lists used to recognize a section header in arbitrary parsed PDF
# text, keyed the same way as SECTION_HEADINGS above (which drives what we
# *write*) so both stay conceptually in sync. This list is intentionally
# generic — it must also recognize section headers in resumes we didn't
# generate ourselves, not just our own SECTION_HEADINGS values.
SECTION_HEADER_SYNONYMS: dict[str, list[str]] = {
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "objective",
        "resumo profissional",
        "resumo",
        "perfil profissional",
        "perfil",
        "sobre mim",
    ],
    "experience": [
        "experience",
        "professional experience",
        "work experience",
        "employment history",
        "work history",
        "experiência profissional",
        "experiencia profissional",
        "experiência",
        "experiencia",
        "histórico profissional",
    ],
    "projects": [
        "projects",
        "personal projects",
        "side projects",
        "projetos",
        "projetos pessoais",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "habilidades técnicas",
        "habilidades tecnicas",
        "habilidades",
        "competências",
        "competencias",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
        "certificações",
        "certificacoes",
        "certificados",
    ],
    "education": [
        "education",
        "academic background",
        "formação acadêmica",
        "formacao academica",
        "formação",
        "formacao",
        "educação",
        "educacao",
    ],
    "languages": [
        "languages",
        "language proficiency",
        "languages spoken",
        "idiomas",
        "línguas",
        "linguas",
    ],
}

# A header line is short by nature ("EXPERIENCE", "Technical Skills") — used
# by the primary bold+uppercase heuristic to reject long bold sentences.
HEADER_MAX_WORDS = 6

# A vertical gap larger than this multiple of the section's typical (median)
# line gap signals a new subsection (e.g. a new job entry). Tuned higher than
# OpenResume's reference 1.4x: our own generator (and many real resumes)
# already inserts a smaller deliberate gap *within* an entry (e.g. before its
# bullet list or a trailing "Technologies used:" line), which a low ratio
# misclassifies as a subsection break against the section's small sample of
# gaps. 2.2x reliably separates entry-to-entry gaps from those intra-entry
# gaps while still relying on the bold-line fallback below for resumes with
# uniform spacing but bolded entry titles.
SUBSECTION_GAP_RATIO = 2.2

# rapidfuzz partial_ratio threshold for the header-synonym fallback match.
HEADER_FUZZY_THRESHOLD = 82
