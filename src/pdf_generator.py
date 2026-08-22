"""ATS-friendly PDF generation using fpdf2."""

import re
from pathlib import Path

from fpdf import FPDF


# Unicode → ASCII replacements for PDF compatibility with core fonts
_UNICODE_REPLACEMENTS = {
    "\u2014": " - ",   # em dash
    "\u2013": "-",     # en dash
    "\u2018": "'",     # left single quote
    "\u2019": "'",     # right single quote
    "\u201c": '"',     # left double quote
    "\u201d": '"',     # right double quote
    "\u2026": "...",   # ellipsis
    "\u2022": "-",     # bullet
    "\u00a0": " ",     # non-breaking space
    "\u2010": "-",     # hyphen
    "\u2011": "-",     # non-breaking hyphen
    "\u2012": "-",     # figure dash
    "\u00b7": "-",     # middle dot
    "\u2023": ">",     # triangular bullet
    "\u2043": "-",     # hyphen bullet
    "\u00e9": "e",     # é
    "\u00e7": "c",     # ç
    "\u00e3": "a",     # ã
    "\u00f3": "o",     # ó
    "\u00ed": "i",     # í
    "\u00e1": "a",     # á
    "\u00ea": "e",     # ê
    "\u00f4": "o",     # ô
    "\u00e0": "a",     # à
    "\u00fc": "u",     # ü
    "\u007e": "~",     # tilde
}


def _sanitize_text(text: str) -> str:
    """Replace Unicode characters with ASCII equivalents for PDF core fonts."""
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    # Remove any remaining non-latin-1 characters
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text

from resume_builder.ats_rules import (
    BULLET_INDENT,
    FONT_FAMILY,
    FONT_SIZE_BODY,
    FONT_SIZE_HEADING,
    FONT_SIZE_NAME,
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBHEADING,
    LINE_HEIGHT,
    PAGE_MARGIN_BOTTOM,
    PAGE_MARGIN_LEFT,
    PAGE_MARGIN_RIGHT,
    PAGE_MARGIN_TOP,
    SECTION_HEADINGS,
    SECTION_SPACING,
)
from resume_builder.selector import SelectedResume


class ResumePDF(FPDF):
    """Custom FPDF class for ATS-friendly resume generation."""

    def __init__(self):
        super().__init__()
        self.set_margins(PAGE_MARGIN_LEFT, PAGE_MARGIN_TOP, PAGE_MARGIN_RIGHT)
        self.set_auto_page_break(auto=True, margin=PAGE_MARGIN_BOTTOM)
        self.add_page()

    def _write_header(self, resume: SelectedResume):
        """Write name and contact information."""
        profile = resume.profile

        # Name
        self.set_font(FONT_FAMILY, "B", FONT_SIZE_NAME)
        self.cell(0, 8, _sanitize_text(profile.name), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        # Contact line
        contact_parts = []
        if profile.email:
            contact_parts.append(profile.email)
        if profile.phone:
            contact_parts.append(profile.phone)
        if profile.location:
            contact_parts.append(profile.location)
        if profile.linkedin:
            contact_parts.append(profile.linkedin)

        if contact_parts:
            self.set_font(FONT_FAMILY, "", FONT_SIZE_SMALL)
            contact_line = "  |  ".join(contact_parts)
            self.cell(0, LINE_HEIGHT, _sanitize_text(contact_line), align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(1)

        # Headline
        if profile.headline:
            self.set_font(FONT_FAMILY, "I", FONT_SIZE_SMALL)
            self.multi_cell(0, LINE_HEIGHT, _sanitize_text(profile.headline), align="C")
            self.ln(1)

        self.ln(SECTION_SPACING)

    def _write_section_heading(self, title: str):
        """Write a section heading with a line separator."""
        self.set_font(FONT_FAMILY, "B", FONT_SIZE_HEADING)
        self.cell(0, LINE_HEIGHT + 1, _sanitize_text(title.upper()), new_x="LMARGIN", new_y="NEXT")
        # Draw a thin line under the heading
        y = self.get_y()
        self.line(PAGE_MARGIN_LEFT, y, self.w - PAGE_MARGIN_RIGHT, y)
        self.ln(3)

    def _write_summary(self, resume: SelectedResume):
        """Write professional summary section."""
        if not resume.summary:
            return
        self._write_section_heading(SECTION_HEADINGS["summary"])
        self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)
        self.multi_cell(0, LINE_HEIGHT, _sanitize_text(resume.summary))
        self.ln(SECTION_SPACING)

    def _write_experience(self, resume: SelectedResume):
        """Write experience section."""
        if not resume.experiences:
            return
        self._write_section_heading(SECTION_HEADINGS["experience"])

        for i, (exp, bullets) in enumerate(resume.experiences):
            # Company and role line
            self.set_font(FONT_FAMILY, "B", FONT_SIZE_SUBHEADING)
            self.cell(0, LINE_HEIGHT, _sanitize_text(exp.role), new_x="LMARGIN", new_y="NEXT")

            self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)
            company_line = exp.company
            if exp.location:
                company_line += f" | {exp.location}"
            company_line += f" | {exp.start_date} - {exp.end_date}"
            self.cell(0, LINE_HEIGHT, _sanitize_text(company_line), new_x="LMARGIN", new_y="NEXT")
            self.ln(1)

            # Description
            if exp.description:
                self.set_font(FONT_FAMILY, "I", FONT_SIZE_BODY)
                self.multi_cell(0, LINE_HEIGHT, _sanitize_text(exp.description))
                self.ln(1)

            # Bullets
            self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)
            for bullet in bullets:
                # Temporarily increase left margin for bullet indentation
                original_margin = self.l_margin
                self.set_left_margin(original_margin + BULLET_INDENT)
                self.set_x(original_margin + BULLET_INDENT)
                self.multi_cell(0, LINE_HEIGHT, _sanitize_text(f"- {bullet.text}"))
                self.set_left_margin(original_margin)

            if i < len(resume.experiences) - 1:
                self.ln(3)

        self.ln(SECTION_SPACING)

    def _write_skills(self, resume: SelectedResume):
        """Write skills section."""
        if not resume.skill_categories:
            return
        self._write_section_heading(SECTION_HEADINGS["skills"])

        self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)
        for cat in resume.skill_categories:
            skill_names = [s.name for s in cat.skills]
            cat_label = _sanitize_text(f"{cat.category}: ")
            self.set_font(FONT_FAMILY, "B", FONT_SIZE_BODY)
            self.cell(self.get_string_width(cat_label), LINE_HEIGHT, cat_label)
            self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)
            remaining = _sanitize_text(", ".join(skill_names))
            self.multi_cell(0, LINE_HEIGHT, remaining)
            self.ln(0.5)

        self.ln(SECTION_SPACING)

    def _write_certifications(self, resume: SelectedResume):
        """Write certifications section."""
        if not resume.certifications:
            return
        self._write_section_heading(SECTION_HEADINGS["certifications"])

        self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)
        for cert in resume.certifications:
            line = cert.name
            if cert.issuer:
                line += f" - {cert.issuer}"
            self.cell(0, LINE_HEIGHT, _sanitize_text(f"- {line}"), new_x="LMARGIN", new_y="NEXT")

        self.ln(SECTION_SPACING)

    def _write_education(self, resume: SelectedResume):
        """Write education section."""
        if not resume.education:
            return
        self._write_section_heading(SECTION_HEADINGS["education"])

        self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)
        for edu in resume.education:
            # Degree and field on first line (bold)
            self.set_font(FONT_FAMILY, "B", FONT_SIZE_BODY)
            degree_line = edu.degree
            if edu.field:
                degree_line += f", {edu.field}"
            self.cell(0, LINE_HEIGHT, _sanitize_text(degree_line), new_x="LMARGIN", new_y="NEXT")

            # Institution and dates on second line
            self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)
            inst_line = edu.institution
            if edu.start_year and edu.end_year:
                inst_line += f" ({edu.start_year} - {edu.end_year})"
            elif edu.end_year:
                inst_line += f" ({edu.end_year})"
            self.cell(0, LINE_HEIGHT, _sanitize_text(inst_line), new_x="LMARGIN", new_y="NEXT")

            if edu.notes:
                self.set_font(FONT_FAMILY, "I", FONT_SIZE_SMALL)
                self.cell(0, LINE_HEIGHT, _sanitize_text(edu.notes), new_x="LMARGIN", new_y="NEXT")
                self.set_font(FONT_FAMILY, "", FONT_SIZE_BODY)

            self.ln(1)

        self.ln(SECTION_SPACING)


def generate_pdf(resume: SelectedResume, output_path: Path) -> Path:
    """Generate an ATS-friendly PDF resume."""
    pdf = ResumePDF()

    # Write header (name + contact)
    pdf._write_header(resume)

    # Write sections in the determined order
    section_writers = {
        "summary": pdf._write_summary,
        "experience": pdf._write_experience,
        "skills": pdf._write_skills,
        "certifications": pdf._write_certifications,
        "education": pdf._write_education,
    }

    for section in resume.section_order:
        writer = section_writers.get(section)
        if writer:
            writer(resume)

    # Save PDF
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    return output_path
