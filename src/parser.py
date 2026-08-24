"""YAML loader with Pydantic validation."""

from pathlib import Path

import yaml

from models import (
    Certification,
    Education,
    Experience,
    ExperienceBullet,
    Profile,
    ResumeData,
    Skill,
    SkillCategory,
)


def load_yaml(path: Path) -> dict | list:
    """Load a YAML file and return parsed content."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_profile(data_dir: Path) -> Profile:
    """Load profile.yaml."""
    data = load_yaml(data_dir / "profile.yaml")
    return Profile(**data)


def load_experiences(data_dir: Path) -> list[Experience]:
    """Load experiences.yaml."""
    data = load_yaml(data_dir / "experiences.yaml")
    experiences = []
    for exp in data:
        bullets = []
        for b in exp.get("bullets", []):
            if isinstance(b, str):
                bullets.append(ExperienceBullet(text=b))
            else:
                bullets.append(ExperienceBullet(**b))
        exp["bullets"] = bullets
        experiences.append(Experience(**exp))
    return experiences


def load_skills(data_dir: Path) -> list[SkillCategory]:
    """Load skills.yaml."""
    data = load_yaml(data_dir / "skills.yaml")
    categories = []
    for cat in data:
        skills = [
            Skill(**s) if isinstance(s, dict) else Skill(name=s)
            for s in cat.get("skills", [])
        ]
        categories.append(SkillCategory(category=cat["category"], skills=skills))
    return categories


def load_certifications(data_dir: Path) -> list[Certification]:
    """Load certifications.yaml."""
    data = load_yaml(data_dir / "certifications.yaml")
    return [
        Certification(**c) if isinstance(c, dict) else Certification(name=c)
        for c in data
    ]


def load_education(data_dir: Path) -> list[Education]:
    """Load education.yaml."""
    data = load_yaml(data_dir / "education.yaml")
    return [Education(**e) for e in data]


def load_resume_data(data_dir: Path) -> ResumeData:
    """Load all YAML files and return a validated ResumeData object."""
    data_dir = Path(data_dir)
    return ResumeData(
        profile=load_profile(data_dir),
        experiences=load_experiences(data_dir),
        skill_categories=load_skills(data_dir),
        certifications=load_certifications(data_dir),
        education=load_education(data_dir),
    )
