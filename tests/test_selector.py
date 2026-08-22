"""Tests for the content selector."""

import pytest

from resume_builder.models import (
    Certification,
    Education,
    Experience,
    ExperienceBullet,
    Profile,
    ResumeData,
    Skill,
    SkillCategory,
)
from resume_builder.selector import select_generic, select_targeted


@pytest.fixture
def sample_resume_data():
    return ResumeData(
        profile=Profile(
            name="Test User",
            email="test@example.com",
            headline="Senior Cloud Architect",
            summary="Experienced cloud architect with Azure and AWS expertise.",
        ),
        experiences=[
            Experience(
                company="Company A",
                role="Cloud Architect",
                start_date="Jan 2023",
                end_date="Present",
                bullets=[
                    ExperienceBullet(text="Designed Azure landing zones", keywords=["Azure"]),
                    ExperienceBullet(text="Implemented Terraform modules", keywords=["Terraform"]),
                    ExperienceBullet(text="Led team of 5 engineers", keywords=["leadership"]),
                    ExperienceBullet(text="Optimized cloud costs by 25%", keywords=["cost"]),
                    ExperienceBullet(text="Built CI/CD pipelines", keywords=["CI/CD"]),
                    ExperienceBullet(text="Managed Kubernetes clusters", keywords=["Kubernetes"]),
                    ExperienceBullet(text="Wrote documentation", keywords=[]),
                ],
            ),
            Experience(
                company="Company B",
                role="Full-Stack Developer",
                start_date="Jan 2020",
                end_date="Dec 2022",
                bullets=[
                    ExperienceBullet(text="Built React applications", keywords=["React"]),
                    ExperienceBullet(text="Developed Node.js APIs", keywords=["Node.js"]),
                ],
            ),
        ],
        skill_categories=[
            SkillCategory(
                category="Cloud",
                skills=[
                    Skill(name="Azure", years=5),
                    Skill(name="AWS", years=3),
                    Skill(name="Terraform", years=4),
                ],
            ),
            SkillCategory(
                category="Languages",
                skills=[
                    Skill(name="TypeScript", years=4),
                    Skill(name="Python", years=3),
                ],
            ),
        ],
        certifications=[
            Certification(name="Azure Solutions Architect Expert", issuer="Microsoft"),
            Certification(name="AWS Cloud Practitioner", issuer="AWS"),
        ],
        education=[
            Education(
                institution="University",
                degree="B.S.",
                field="Computer Science",
                start_year=2016,
                end_year=2020,
            ),
        ],
    )


class TestSelectGeneric:
    def test_includes_all_experiences(self, sample_resume_data):
        result = select_generic(sample_resume_data)
        assert len(result.experiences) == 2

    def test_limits_bullets(self, sample_resume_data):
        result = select_generic(sample_resume_data)
        # First experience has 7 bullets, should be limited to MAX_BULLETS_PER_EXPERIENCE (6)
        _, bullets = result.experiences[0]
        assert len(bullets) <= 6

    def test_includes_all_certifications(self, sample_resume_data):
        result = select_generic(sample_resume_data)
        assert len(result.certifications) == 2

    def test_default_section_order(self, sample_resume_data):
        result = select_generic(sample_resume_data)
        assert result.section_order[0] == "summary"
        assert "experience" in result.section_order
        assert "skills" in result.section_order


class TestSelectTargeted:
    def test_prioritizes_relevant_experience(self, sample_resume_data):
        scored = {
            "jd_keywords": ["azure", "terraform", "cloud", "kubernetes"],
            "scored_skills": [
                ("Cloud", Skill(name="Azure", years=5), 1.3),
                ("Cloud", Skill(name="Terraform", years=4), 1.2),
                ("Cloud", Skill(name="AWS", years=3), 0.8),
                ("Languages", Skill(name="TypeScript", years=4), 0.1),
                ("Languages", Skill(name="Python", years=3), 0.1),
            ],
            "scored_experiences": [
                (
                    sample_resume_data.experiences[0],
                    0.8,
                    [(b, 0.5 + i * 0.05) for i, b in enumerate(sample_resume_data.experiences[0].bullets)],
                ),
                (
                    sample_resume_data.experiences[1],
                    0.2,
                    [(b, 0.1) for b in sample_resume_data.experiences[1].bullets],
                ),
            ],
            "scored_certifications": [
                (sample_resume_data.certifications[0], 0.9),
                (sample_resume_data.certifications[1], 0.3),
            ],
            "overall_score": 0.65,
        }
        result = select_targeted(sample_resume_data, scored)

        # Cloud architect experience should rank first
        assert result.experiences[0][0].role == "Cloud Architect"
        assert result.match_score == 0.65

    def test_limits_bullets_targeted(self, sample_resume_data):
        scored = {
            "jd_keywords": ["azure"],
            "scored_skills": [("Cloud", Skill(name="Azure", years=5), 1.0)],
            "scored_experiences": [
                (
                    sample_resume_data.experiences[0],
                    0.8,
                    [(b, 0.5) for b in sample_resume_data.experiences[0].bullets],
                ),
            ],
            "scored_certifications": [],
            "overall_score": 0.5,
        }
        result = select_targeted(sample_resume_data, scored)
        _, bullets = result.experiences[0]
        assert len(bullets) <= 5  # MAX_BULLETS_PER_EXPERIENCE_TARGETED
