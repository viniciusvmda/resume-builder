"""Generic PDF text/section extraction, simulating how a real ATS parser reads a resume.

This module never assumes the PDF came from pdf_generator.py, and never
assumes known field names inside a section — only text lines and simple
visual formatting cues (bold, vertical position, bullet markers). That is
deliberately how real ATS parsers (Workday, Greenhouse, iCIMS, ...) work:
they extract the PDF's text stream, detect section headers via a
bold+uppercase heuristic (falling back to fuzzy-matching common header
words), split entries within a section by vertical whitespace/bold-line
cues, and never see the source data's original structure.
"""

import statistics
from pathlib import Path
from typing import NamedTuple

import pdfplumber
from rapidfuzz import fuzz

from ats_rules import (
    HEADER_FUZZY_THRESHOLD,
    HEADER_MAX_WORDS,
    SECTION_HEADER_SYNONYMS,
    SUBSECTION_GAP_RATIO,
)
from text_patterns import BULLET_PREFIX_RE

# Chars whose "top" coordinate differs by less than this (in points) are
# considered part of the same visual line.
LINE_GROUP_TOLERANCE = 2.0


class Line(NamedTuple):
    text: str
    top: float
    bottom: float
    bold: bool
    is_bullet: bool
    page: int


class Subsection(NamedTuple):
    """One entry within a section (e.g. one job or one project).

    header_text deliberately keeps role/company/dates/description merged as
    one blob — splitting those apart would require assuming a known field
    layout, which a real ATS parser can't do either.
    """

    header_text: str
    bullet_lines: list[str]


class Section(NamedTuple):
    heading_raw: str | None
    heading_key: str | None
    lines: list[Line]
    subsections: list[Subsection]
    text: str


class ParsedResume(NamedTuple):
    raw_text: str
    sections: list[Section]
    preamble_text: str


def extract_lines(pdf_path: Path) -> list[Line]:
    """Extract visual text lines (with bold/bullet metadata) from a PDF.

    Vertical positions are offset cumulatively across pages so gap-based
    subsection splitting works across a page break the same way it does
    within a single page.
    """
    lines: list[Line] = []
    y_offset = 0.0

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            chars = sorted(page.chars, key=lambda c: (round(c["top"], 1), c["x0"]))
            groups: list[list[dict]] = []
            for c in chars:
                if groups and abs(c["top"] - groups[-1][-1]["top"]) <= LINE_GROUP_TOLERANCE:
                    groups[-1].append(c)
                else:
                    groups.append([c])

            for group in groups:
                group.sort(key=lambda c: c["x0"])
                text = "".join(c["text"] for c in group).strip()
                if not text:
                    continue
                top = min(c["top"] for c in group) + y_offset
                bottom = max(c["bottom"] for c in group) + y_offset
                bold_count = sum(
                    1 for c in group if "bold" in c.get("fontname", "").lower()
                )
                bold = bold_count > len(group) / 2
                is_bullet = bool(BULLET_PREFIX_RE.match(text))
                lines.append(Line(text, top, bottom, bold, is_bullet, page_index))

            y_offset += page.height

    return lines


def _is_header_candidate(line: Line) -> bool:
    """Header lines are short and not bullet items — filters out long prose
    sentences before either header heuristic runs."""
    words = line.text.split()
    return 0 < len(words) <= HEADER_MAX_WORDS and not line.is_bullet


def classify_header(line_text: str) -> str | None:
    """Fuzzy-match a line's text against known section header synonyms,
    returning the canonical key (e.g. "experience") or None.

    Uses token_set_ratio (word-overlap based), not partial_ratio: partial_ratio
    scores the best-matching substring by raw character similarity, which
    gives false positives on short unrelated phrases that happen to share a
    character sequence (e.g. a wrapped bullet fragment like "reached
    production" scores 87.5 against "education" under partial_ratio, comfortably
    above threshold, purely from coincidental character overlap — token_set_ratio
    scores that pair at 51.9). token_set_ratio still correctly scores 100 for
    genuine superset/subset phrasings like "technical skills" vs "skills".
    """
    normalized = line_text.strip().rstrip(":").lower()
    if not normalized:
        return None

    best_key: str | None = None
    best_score = 0.0
    for key, synonyms in SECTION_HEADER_SYNONYMS.items():
        for synonym in synonyms:
            score = fuzz.token_set_ratio(normalized, synonym)
            if score > best_score:
                best_score = score
                best_key = key

    return best_key if best_score >= HEADER_FUZZY_THRESHOLD else None


def is_section_header(line: Line) -> bool:
    """Primary heuristic: bold + uppercase + short. Fallback: fuzzy-match
    against known header synonyms regardless of bold/case."""
    if not _is_header_candidate(line):
        return False
    if line.bold and line.text.isupper():
        return True
    return classify_header(line.text) is not None


def split_into_subsections(lines: list[Line]) -> list[Subsection]:
    """Split a section's lines into subsections (e.g. separate job entries).

    Splits at a vertical gap significantly larger than the section's typical
    line gap, with a fallback: a bold non-bullet line starting fresh content
    also signals a new entry (covers same-density layouts).

    Gaps are only measured between lines on the same page: a page break
    produces a large but meaningless vertical delta (bottom margin of one
    page plus top margin of the next), which would otherwise look like a
    subsection separator even when an entry is simply split across pages by
    normal pagination. Across a page break, only the bold-line fallback
    applies.
    """
    if not lines:
        return []

    gaps = [
        lines[i].top - lines[i - 1].bottom
        for i in range(1, len(lines))
        if lines[i].top > lines[i - 1].bottom and lines[i].page == lines[i - 1].page
    ]
    median_gap = statistics.median(gaps) if gaps else 0.0

    subsections: list[Subsection] = []
    current_header_lines: list[str] = []
    current_bullets: list[str] = []

    def flush():
        if current_header_lines or current_bullets:
            subsections.append(
                Subsection(
                    header_text=" ".join(current_header_lines).strip(),
                    bullet_lines=list(current_bullets),
                )
            )

    for i, line in enumerate(lines):
        has_content = bool(current_header_lines or current_bullets)
        gap_break = False
        if i > 0 and median_gap > 0 and line.page == lines[i - 1].page:
            gap = line.top - lines[i - 1].bottom
            gap_break = gap > median_gap * SUBSECTION_GAP_RATIO
        bold_break = has_content and line.bold and not line.is_bullet

        if has_content and (gap_break or bold_break):
            flush()
            current_header_lines = []
            current_bullets = []

        if line.is_bullet:
            current_bullets.append(BULLET_PREFIX_RE.sub("", line.text))
        else:
            current_header_lines.append(line.text)

    flush()
    return subsections


def split_into_sections(lines: list[Line]) -> tuple[str, list[Section]]:
    """Walk lines, starting a new Section at each detected header. Lines
    before the first header become the preamble (name/contact/headline)."""
    sections: list[Section] = []
    preamble_lines: list[str] = []
    current_lines: list[Line] = []
    current_heading_raw: str | None = None
    current_heading_key: str | None = None

    def flush():
        if current_heading_raw is not None:
            text = "\n".join(l.text for l in current_lines)
            sections.append(
                Section(
                    heading_raw=current_heading_raw,
                    heading_key=current_heading_key,
                    lines=list(current_lines),
                    subsections=split_into_subsections(current_lines),
                    text=text,
                )
            )

    for line in lines:
        if is_section_header(line):
            flush()
            current_heading_raw = line.text
            current_heading_key = classify_header(line.text)
            current_lines = []
        elif current_heading_raw is None:
            preamble_lines.append(line.text)
        else:
            current_lines.append(line)

    flush()
    return "\n".join(preamble_lines), sections


def parse_resume_pdf(pdf_path: Path) -> ParsedResume:
    """Top-level entry point: PDF file -> ParsedResume."""
    lines = extract_lines(pdf_path)
    raw_text = "\n".join(l.text for l in lines)
    preamble_text, sections = split_into_sections(lines)
    return ParsedResume(raw_text=raw_text, sections=sections, preamble_text=preamble_text)
