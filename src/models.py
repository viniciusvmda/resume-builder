"""Pydantic models for structured career YAML data."""

from pydantic import BaseModel, ConfigDict


class Profile(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None


class ExperienceBullet(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str


class Experience(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str
    role: str
    start_date: str
    end_date: str = "Present"
    location: str | None = None
    description: str | None = None
    keywords: list[str] = []
    bullets: list[ExperienceBullet] = []


class Skill(BaseModel):
    name: str
    years: float | None = None
    aliases: list[str] = []


class SkillCategory(BaseModel):
    category: str
    skills: list[Skill]


class Certification(BaseModel):
    name: str
    issuer: str | None = None
    date: str | None = None


class Education(BaseModel):
    institution: str
    degree: str
    field: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    notes: str | None = None


class ResumeData(BaseModel):
    """Complete resume data loaded from YAML files."""

    profile: Profile
    experiences: list[Experience] = []
    skill_categories: list[SkillCategory] = []
    certifications: list[Certification] = []
    education: list[Education] = []
