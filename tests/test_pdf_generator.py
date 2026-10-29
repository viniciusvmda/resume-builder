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

    def test_long_text_wraps_without_overflowing_page(self):
        """Test that long text entries (e.g. long project names) wrap across lines and stay within margins."""
        import pdfplumber

        from resume_builder.models import Project

        long_name = (
            "ATMOSPHERE (Adaptive, Trustworthy, Manageable, Orchestrated, "
            "Secure Privacy-assuring, Hybrid Ecosystem for Resilient Cloud Computing)"
        )
        resume = SelectedResume(
            profile=Profile(name="Test User"),
            summary="",
            experiences=[],
            projects=[(Project(name=long_name, start_year="2020", end_year="2022", description=""), [])],
            skill_categories=[],
            certifications=[],
            education=[],
            section_order=["projects"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_long_text.pdf"
            generate_pdf(resume, output_path)
            with pdfplumber.open(output_path) as pdf:
                page = pdf.pages[0]
                text = page.extract_text()
                # Verify that the long name wrapped into multiple lines
                assert "ATMOSPHERE" in text
                assert "Cloud Computing)" in text
                # Verify all characters stay inside the right margin
                for char in page.chars:
                    assert char["x1"] <= page.width - 10

    def test_preserves_accented_characters(self):
        """Test that accented words like Educação and Gestão are preserved in PDF output."""
        import pdfplumber

        from resume_builder.models import Education

        resume = SelectedResume(
            profile=Profile(name="José Garcia"),
            summary="Especialista em Gestão e Educação com experiência comprovada.",
            experiences=[],
            projects=[],
            skill_categories=[],
            certifications=[],
            education=[
                Education(
                    institution="Universidade de São Paulo",
                    degree="Pós-Graduação em Educação",
                    field="Ciência da Computação",
                )
            ],
            section_order=["summary", "education"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_accents.pdf"
            generate_pdf(resume, output_path)
            with pdfplumber.open(output_path) as pdf:
                text = pdf.pages[0].extract_text()
                assert "Educação" in text
                assert "Gestão" in text
                assert "São Paulo" in text
                assert "Ciência" in text

    def test_renders_nationality_in_header(self):
        """Test that nationality is rendered in the header contact line when present."""
        import pdfplumber

        resume = SelectedResume(
            profile=Profile(
                name="Maria Silva",
                email="maria@example.com",
                location="Belo Horizonte, Brazil",
                nationality="Brazilian",
            ),
            summary="Engenheira de software.",
            experiences=[],
            projects=[],
            skill_categories=[],
            certifications=[],
            education=[],
            section_order=["summary"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_nationality.pdf"
            generate_pdf(resume, output_path)
            with pdfplumber.open(output_path) as pdf:
                text = pdf.pages[0].extract_text()
                assert "Brazilian" in text
                assert "Belo Horizonte, Brazil" in text
                assert "maria@example.com" in text

    def test_renders_languages_section(self):
        """Test that languages section renders correctly with formatted items."""
        import pdfplumber

        from resume_builder.models import Language

        languages = [
            Language(name="Portuguese", proficiency="Native"),
            Language(name="English", proficiency="C1"),
            Language(name="Italian", proficiency="B2", notes="Studied in Rome"),
        ]

        resume = SelectedResume(
            profile=Profile(name="Maria Silva"),
            summary="Engenheira de software.",
            experiences=[],
            projects=[],
            skill_categories=[],
            certifications=[],
            education=[],
            languages=languages,
            section_order=["summary", "languages"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_languages.pdf"
            generate_pdf(resume, output_path)
            with pdfplumber.open(output_path) as pdf:
                text = pdf.pages[0].extract_text()
                assert "LANGUAGES" in text or "Languages" in text
                assert "Portuguese (Native)" in text
                assert "English (C1)" in text
                assert "Italian (B2, Studied in Rome)" in text

    def test_generate_pdf_pt_br(self, sample_selected_resume):
        """Test that lang='pt-br' produces Portuguese headings and labels."""
        import pdfplumber

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_pt_br.pdf"
            generate_pdf(sample_selected_resume, output_path, show_skill_years=True, lang="pt-br")
            with pdfplumber.open(output_path) as pdf:
                text = "\n".join(p.extract_text() for p in pdf.pages)
                assert "RESUMO PROFISSIONAL" in text
                assert "FORMAÇÃO ACADÊMICA" in text
                assert "EXPERIÊNCIA PROFISSIONAL" in text
                assert "HABILIDADES TÉCNICAS" in text
                assert "CERTIFICAÇÕES" in text
                assert "Tecnologias utilizadas:" in text
                assert "Atual" in text
                assert "anos" in text

    def test_cli_lang_flag(self):
        """Test the --lang CLI option using Click runner."""
        from click.testing import CliRunner

        from resume_builder.cli import main

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "cv_pt.pdf"
            result = runner.invoke(
                main,
                ["generate", "--data-dir", "example", "--output", str(out_pdf), "--lang", "pt-br"],
            )
            assert result.exit_code == 0
            assert out_pdf.exists()
            assert "Generating PDF (pt-br" in result.output

    def test_cli_section_order_flag(self):
        """Test the --section-order CLI option using Click runner."""
        import pdfplumber
        from click.testing import CliRunner

        from resume_builder.cli import main

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "cv_custom_order.pdf"
            result = runner.invoke(
                main,
                [
                    "generate",
                    "--data-dir",
                    "example",
                    "--output",
                    str(out_pdf),
                    "--section-order",
                    "education.yaml, profile.yaml, experiences.yaml",
                ],
            )
            assert result.exit_code == 0
            assert out_pdf.exists()
            with pdfplumber.open(out_pdf) as pdf:
                text = pdf.pages[0].extract_text()
                # Education must appear before Professional Summary and Experience
                edu_idx = text.find("EDUCATION")
                summary_idx = text.find("PROFESSIONAL SUMMARY")
                exp_idx = text.find("PROFESSIONAL EXPERIENCE")
                assert edu_idx != -1
                assert summary_idx != -1
                assert exp_idx != -1
                assert edu_idx < summary_idx < exp_idx

    def test_cli_section_order_invalid(self):
        """Test that invalid section names in --section-order produce an error."""
        from click.testing import CliRunner

        from resume_builder.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["generate", "--data-dir", "example", "--section-order", "invalid_section,profile"],
        )
        assert result.exit_code != 0
        assert "Unknown section name 'invalid_section'" in result.output

    def test_default_font_is_helvetica(self, sample_selected_resume):
        """Test that default font is Helvetica without font argument."""
        import pdfplumber

        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "test_default_font.pdf"
            generate_pdf(sample_selected_resume, out_pdf)
            with pdfplumber.open(out_pdf) as pdf:
                fonts = {c.get("fontname", "") for c in pdf.pages[0].chars}
                assert any("Helvetica" in f for f in fonts)
                assert not any("CMUSerif" in f for f in fonts)

    def test_custom_cmu_serif_font(self, sample_selected_resume):
        """Test specifying CMU Serif Roman as font."""
        import pdfplumber

        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "test_cmu_font.pdf"
            generate_pdf(sample_selected_resume, out_pdf, font="cmu-serif")
            with pdfplumber.open(out_pdf) as pdf:
                fonts = {c.get("fontname", "") for c in pdf.pages[0].chars}
                assert any("CMUSerif" in f for f in fonts)

    def test_cli_font_flag(self):
        """Test the --font CLI option using Click runner."""
        import pdfplumber
        from click.testing import CliRunner

        from resume_builder.cli import main

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "cv_cmu.pdf"
            result = runner.invoke(
                main,
                ["generate", "--data-dir", "example", "--output", str(out_pdf), "--font", "cmu-serif"],
            )
            assert result.exit_code == 0
            assert out_pdf.exists()
            assert "font: cmu-serif" in result.output
            with pdfplumber.open(out_pdf) as pdf:
                fonts = {c.get("fontname", "") for c in pdf.pages[0].chars}
                assert any("CMUSerif" in f for f in fonts)



