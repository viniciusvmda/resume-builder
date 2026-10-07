"""Tests for PDF generation."""

import tempfile
from pathlib import Path

from resume_builder.models import Profile
from resume_builder.pdf_generator import generate_pdf
from resume_builder.selector import SelectedResume


class TestGeneratePDF:
    def test_creates_pdf_file(self, sample_selected_resume):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_resume.pdf"
            result = generate_pdf(sample_selected_resume, output_path)
            assert result.exists()
            assert result.stat().st_size > 0

    def test_pdf_is_valid(self, sample_selected_resume):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_resume.pdf"
            generate_pdf(sample_selected_resume, output_path)
            # Check PDF magic bytes
            with open(output_path, "rb") as f:
                header = f.read(5)
            assert header == b"%PDF-"

    def test_handles_unicode_characters(self):
        """Test that Unicode characters like em-dashes don't crash the PDF."""
        resume = SelectedResume(
            profile=Profile(
                name="Jose Garcia",
                headline="Cloud Architect - Azure & AWS",
                summary="Experienced architect - delivered 50+ projects across multiple regions.",
            ),
            summary="Experienced architect - delivered 50+ projects across multiple regions.",
            experiences=[],
            skill_categories=[],
            certifications=[],
            education=[],
            section_order=["summary"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_unicode.pdf"
            result = generate_pdf(resume, output_path)
            assert result.exists()

    def test_creates_parent_directories(self, sample_selected_resume):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "resume.pdf"
            result = generate_pdf(sample_selected_resume, output_path)
            assert result.exists()
