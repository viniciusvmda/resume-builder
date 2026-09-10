"""Shared pytest fixtures."""

import pytest

from models import (
    Bullet,
    Certification,
    Education,
    Experience,
    ExperienceBullet,
    Profile,
    Project,
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
                    technologies=["Azure", "Terraform", "cost optimization"],
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
        projects=[
            (
                Project(
                    name="Open-Source Rate Limiter",
                    start_year="2022",
                    end_year="2023",
                    description="A Redis-backed distributed rate limiter.",
                    technologies=["Go", "Redis", "distributed systems"],
                    bullets=[
                        Bullet(text="Implemented a Redis-backed sliding window"),
                        Bullet(text="Published as an open-source module"),
                    ],
                ),
                [
                    Bullet(text="Implemented a Redis-backed sliding window"),
                    Bullet(text="Published as an open-source module"),
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
            "projects",
            "certifications",
            "education",
            "skills",
        ],
    )


@pytest.fixture
def generated_pdf_path(tmp_path, sample_selected_resume):
    return generate_pdf(sample_selected_resume, tmp_path / "resume.pdf")
