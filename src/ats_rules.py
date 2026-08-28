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
