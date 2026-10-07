"""Small shared text-pattern constants used by both scorer.py and pdf_parser.py.

Kept separate from scorer.py to avoid a circular import: pdf_parser.py needs
BULLET_PREFIX_RE, and scorer.py needs the PDF-parsed types from pdf_parser.py.
"""

import re

BULLET_PREFIX_RE = re.compile(r"^[-•*]\s*")
