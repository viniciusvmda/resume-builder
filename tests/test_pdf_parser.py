"""Tests for the generic PDF text/section extraction layer."""

from pathlib import Path

from fpdf import FPDF

from pdf_parser import (
    classify_header,
    is_section_header,
    parse_resume_pdf,
    split_into_subsections,
)


def _build_pdf(path: Path, writer) -> Path:
    pdf = FPDF()
    pdf.add_page()
    writer(pdf)
    pdf.output(str(path))
    return path


class TestIsSectionHeader:
    def test_bold_uppercase_short_line_is_header(self, tmp_path):
        pdf_path = _build_pdf(
            tmp_path / "a.pdf",
            lambda pdf: (
                pdf.set_font("Helvetica", "B", 12),
                pdf.cell(0, 10, "EXPERIENCE", new_x="LMARGIN", new_y="NEXT"),
            ),
        )
        from pdf_parser import extract_lines

        lines = extract_lines(pdf_path)
        assert len(lines) == 1
        assert is_section_header(lines[0])
        assert classify_header(lines[0].text) == "experience"

    def test_bold_uppercase_long_sentence_is_not_header(self, tmp_path):
        pdf_path = _build_pdf(
            tmp_path / "b.pdf",
            lambda pdf: (
                pdf.set_font("Helvetica", "B", 10),
                pdf.multi_cell(
                    0,
                    5,
                    "THIS IS A VERY LONG BOLD UPPERCASE SENTENCE ABOUT EXPERIENCE",
                ),
            ),
        )
        from pdf_parser import extract_lines

        lines = extract_lines(pdf_path)
        assert len(lines) == 1
        assert not is_section_header(lines[0])

    def test_plain_text_header_matches_via_synonym_fallback(self, tmp_path):
        pdf_path = _build_pdf(
            tmp_path / "c.pdf",
            lambda pdf: (
                pdf.set_font("Helvetica", "", 10),
                pdf.cell(0, 10, "Work History", new_x="LMARGIN", new_y="NEXT"),
            ),
        )
        from pdf_parser import extract_lines

        lines = extract_lines(pdf_path)
        assert len(lines) == 1
        assert is_section_header(lines[0])
        assert classify_header(lines[0].text) == "experience"

    def test_bold_non_uppercase_short_line_is_not_header(self, tmp_path):
        """A bold job title like 'Senior Engineer' must not be mistaken for
        a section header (guards against false positives on subsection titles)."""
        pdf_path = _build_pdf(
            tmp_path / "d.pdf",
            lambda pdf: (
                pdf.set_font("Helvetica", "B", 10),
                pdf.cell(0, 10, "Senior Engineer", new_x="LMARGIN", new_y="NEXT"),
            ),
        )
        from pdf_parser import extract_lines

        lines = extract_lines(pdf_path)
        assert len(lines) == 1
        assert not is_section_header(lines[0])


class TestSplitIntoSubsections:
    def test_large_vertical_gap_splits_into_two_subsections(self, tmp_path):
        def writer(pdf):
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 5, "Job One", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, "Company One", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(20)  # large gap
            pdf.cell(0, 5, "Job Two", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, "Company Two", new_x="LMARGIN", new_y="NEXT")

        pdf_path = _build_pdf(tmp_path / "e.pdf", writer)
        from pdf_parser import extract_lines

        lines = extract_lines(pdf_path)
        subsections = split_into_subsections(lines)
        assert len(subsections) == 2
        assert "Job One" in subsections[0].header_text
        assert "Job Two" in subsections[1].header_text

    def test_bold_line_fallback_splits_same_density_entries(self, tmp_path):
        def writer(pdf):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 5, "Job One", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 5, "Company One", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 5, "Job Two", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 5, "Company Two", new_x="LMARGIN", new_y="NEXT")

        pdf_path = _build_pdf(tmp_path / "f.pdf", writer)
        from pdf_parser import extract_lines

        lines = extract_lines(pdf_path)
        subsections = split_into_subsections(lines)
        assert len(subsections) == 2

    def test_bullet_lines_extracted_separately_from_header_text(self, tmp_path):
        def writer(pdf):
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 5, "Job One", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, "- Did a thing", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, "- Did another thing", new_x="LMARGIN", new_y="NEXT")

        pdf_path = _build_pdf(tmp_path / "g.pdf", writer)
        from pdf_parser import extract_lines

        lines = extract_lines(pdf_path)
        subsections = split_into_subsections(lines)
        assert len(subsections) == 1
        assert subsections[0].bullet_lines == ["Did a thing", "Did another thing"]
        assert "Job One" in subsections[0].header_text


class TestParseResumePdfEndToEnd:
    def test_recovers_expected_sections_from_generated_pdf(self, generated_pdf_path):
        parsed = parse_resume_pdf(generated_pdf_path)
        heading_keys = {s.heading_key for s in parsed.sections}
        assert {
            "summary",
            "experience",
            "projects",
            "certifications",
            "skills",
        } <= heading_keys

    def test_experience_section_has_one_subsection_per_job(self, generated_pdf_path):
        parsed = parse_resume_pdf(generated_pdf_path)
        experience_section = next(
            s for s in parsed.sections if s.heading_key == "experience"
        )
        assert len(experience_section.subsections) == 1
        assert "Senior Cloud Architect" in experience_section.subsections[0].header_text
