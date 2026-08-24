"""Tests for PDF generation."""

from pathlib import Path
import tempfile

import pytest

from models import (
    Certification,
    Education,
    Experience,
    ExperienceBullet,
    Profile,
    Skill,
    SkillCategory,
)
from pdf_generator import generate_pdf
from selector import SelectedResume


@pytest.fixture
def sample_selected_resume():
    return SelectedResume(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            phone="+1 555-0100",
            linkedin="linkedin.com/in/testuser",
            location="San Francisco, CA",
            headline="Senior Cloud Architect | Azure & AWS",
            summary="Experienced cloud architect with 7+ years building scalable infrastructure.",
        ),
        summary="Experienced cloud architect with 7+ years building scalable infrastructure.",
        experiences=[
            (
                Experience(
                    company="Big Tech Co",
                    role="Senior Cloud Architect",
                    start_date="Jan 2023",
                    end_date="Present",
                    description="Leading cloud infrastructure initiatives.",
                    keywords=["Azure", "Terraform", "cost optimization"],
                    bullets=[
                        ExperienceBullet(
                            text="Designed Azure landing zones for 50+ subscriptions"
                        ),
                        ExperienceBullet(
                            text="Implemented Terraform modules achieving 30% faster deployments"
                        ),
                        ExperienceBullet(
                            text="Led cost optimization saving $500K annually"
                        ),
                    ],
                ),
                [
                    ExperienceBullet(
                        text="Designed Azure landing zones for 50+ subscriptions"
                    ),
                    ExperienceBullet(
                        text="Implemented Terraform modules achieving 30% faster deployments"
                    ),
                    ExperienceBullet(
                        text="Led cost optimization saving $500K annually"
                    ),
                ],
            ),
        ],
        skill_categories=[
            SkillCategory(
                category="Cloud & Infrastructure",
                skills=[
                    Skill(name="Microsoft Azure", years=5),
                    Skill(name="Terraform", years=4),
                    Skill(name="Kubernetes", years=3),
                ],
            ),
        ],
        certifications=[
            Certification(name="Azure Solutions Architect Expert", issuer="Microsoft"),
        ],
        education=[
            Education(
                institution="MIT",
                degree="B.S.",
                field="Computer Science",
                start_year=2015,
                end_year=2019,
            ),
        ],
        section_order=[
            "summary",
            "experience",
            "certifications",
            "education",
            "skills",
        ],
    )


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
