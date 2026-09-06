"""ATS formatting rules and constants."""

# Standard section headings that ATS systems recognize
SECTION_HEADINGS = {
    "summary": "Professional Summary",
    "experience": "Professional Experience",
    "projects": "Projects",
    "skills": "Technical Skills",
    "certifications": "Certifications",
    "education": "Education",
}

# Section order for generic resume (no JD)
DEFAULT_SECTION_ORDER = [
    "summary",
    "experience",
    "projects",
    "certifications",
    "education",
    "skills",
]

# PDF formatting constants
FONT_FAMILY = "Helvetica"
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
    "summary": ["summary", "professional summary", "profile", "objective"],
    "experience": [
        "experience",
        "professional experience",
        "work experience",
        "employment history",
        "work history",
    ],
    "projects": ["projects", "personal projects", "side projects"],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
    ],
    "certifications": ["certifications", "certificates", "licenses"],
    "education": ["education", "academic background"],
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
