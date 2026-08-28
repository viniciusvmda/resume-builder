"""Content selection and ranking logic."""

from ats_rules import (
    DEFAULT_SECTION_ORDER,
    MAX_BULLETS_PER_EXPERIENCE,
    MAX_BULLETS_PER_EXPERIENCE_TARGETED,
    MAX_BULLETS_PER_PROJECT,
    MAX_BULLETS_PER_PROJECT_TARGETED,
    MAX_SKILLS_PER_CATEGORY,
)
from models import (
    Bullet,
    Certification,
    Education,
    Experience,
    ExperienceBullet,
    Profile,
    Project,
    ResumeData,
    Skill,
    SkillCategory,
)


class SelectedResume:
    """Resume content after selection and ordering."""

    def __init__(
        self,
        profile: Profile,
        summary: str | None,
        experiences: list[tuple[Experience, list[ExperienceBullet]]],
        skill_categories: list[SkillCategory],
        certifications: list[Certification],
        education: list[Education],
        section_order: list[str],
        match_score: float | None = None,
        projects: list[tuple[Project, list[Bullet]]] | None = None,
    ):
        self.profile = profile
        self.summary = summary
        self.experiences = experiences
        self.projects = projects if projects is not None else []
        self.skill_categories = skill_categories
        self.certifications = certifications
        self.education = education
        self.section_order = section_order
        self.match_score = match_score


def select_generic(resume_data: ResumeData) -> SelectedResume:
    """Select content for a generic resume (no job description targeting)."""
    # Include all experiences with limited bullets
    experiences = []
    for exp in resume_data.experiences:
        bullets = exp.bullets[:MAX_BULLETS_PER_EXPERIENCE]
        experiences.append((exp, bullets))

    # Include all projects with limited bullets
    projects = []
    for proj in resume_data.projects:
        bullets = proj.bullets[:MAX_BULLETS_PER_PROJECT]
        projects.append((proj, bullets))

    # Include all skill categories with limited skills
    skill_categories = []
    for cat in resume_data.skill_categories:
        limited_skills = cat.skills[:MAX_SKILLS_PER_CATEGORY]
        skill_categories.append(
            SkillCategory(category=cat.category, skills=limited_skills)
        )

    return SelectedResume(
        profile=resume_data.profile,
        summary=resume_data.profile.summary,
        experiences=experiences,
        projects=projects,
        skill_categories=skill_categories,
        certifications=resume_data.certifications,
        education=resume_data.education,
        section_order=DEFAULT_SECTION_ORDER,
    )


def select_targeted(
    resume_data: ResumeData,
    scored: dict,
    rank_experiences: bool = True,
) -> SelectedResume:
    """Select and rank content based on job description scoring."""
    scored_skills: list[tuple[str, Skill, float]] = scored["scored_skills"]
    scored_experiences: list[
        tuple[Experience, float, list[tuple[ExperienceBullet, float]]]
    ] = scored["scored_experiences"]
    scored_projects: list[tuple[Project, float, list[tuple[Bullet, float]]]] = (
        scored.get("scored_projects", [])
    )
    scored_certs: list[tuple[Certification, float]] = scored["scored_certifications"]
    overall_score: float = scored["overall_score"]

    # Optionally rank experiences by score (highest first).
    # When disabled, preserve YAML order from resume_data via scored_experiences.
    sorted_experiences = scored_experiences
    if rank_experiences:
        sorted_experiences = sorted(
            scored_experiences, key=lambda x: x[1], reverse=True
        )

    # Select top bullets per experience
    experiences = []
    for exp, _, bullet_scores in sorted_experiences:
        sorted_bullets = sorted(bullet_scores, key=lambda x: x[1], reverse=True)
        top_bullets = [
            b for b, _ in sorted_bullets[:MAX_BULLETS_PER_EXPERIENCE_TARGETED]
        ]
        # Restore original order for selected bullets
        original_order = {id(b): i for i, b in enumerate(exp.bullets)}
        top_bullets.sort(key=lambda b: original_order.get(id(b), 0))
        experiences.append((exp, top_bullets))

    # Select top bullets per project (same order-restoring pattern as experiences)
    sorted_projects = sorted(scored_projects, key=lambda x: x[1], reverse=True)
    projects = []
    for proj, _, bullet_scores in sorted_projects:
        sorted_bullets = sorted(bullet_scores, key=lambda x: x[1], reverse=True)
        top_bullets = [b for b, _ in sorted_bullets[:MAX_BULLETS_PER_PROJECT_TARGETED]]
        original_order = {id(b): i for i, b in enumerate(proj.bullets)}
        top_bullets.sort(key=lambda b: original_order.get(id(b), 0))
        projects.append((proj, top_bullets))

    # Sort skills within categories by relevance score
    skill_by_category: dict[str, list[tuple[Skill, float]]] = {}
    for category, skill, score in scored_skills:
        if category not in skill_by_category:
            skill_by_category[category] = []
        skill_by_category[category].append((skill, score))

    # Build skill categories ordered by max skill score in category
    category_scores = {
        cat: max(s for _, s in skills) if skills else 0.0
        for cat, skills in skill_by_category.items()
    }
    sorted_categories = sorted(
        category_scores.items(), key=lambda x: x[1], reverse=True
    )

    skill_categories = []
    for cat_name, _ in sorted_categories:
        cat_skills = skill_by_category[cat_name]
        # Sort skills by score within category, take top N
        sorted_cat_skills = sorted(cat_skills, key=lambda x: x[1], reverse=True)
        top_skills = [s for s, _ in sorted_cat_skills[:MAX_SKILLS_PER_CATEGORY]]
        if top_skills:
            skill_categories.append(SkillCategory(category=cat_name, skills=top_skills))

    # Sort certifications by relevance
    sorted_certs = sorted(scored_certs, key=lambda x: x[1], reverse=True)
    certifications = [c for c, _ in sorted_certs]

    # Determine section order based on what scores highest
    section_scores = {
        "experience": max((s for _, s, _ in scored_experiences), default=0.0),
        "projects": max((s for _, s, _ in scored_projects), default=0.0),
        "certifications": max((s for _, s in scored_certs), default=0.0),
    }
    # Summary, education, and skills always in fixed positions (skills last)
    dynamic_sections = sorted(
        ["experience", "projects", "certifications"],
        key=lambda s: section_scores.get(s, 0.0),
        reverse=True,
    )
    section_order = ["summary"] + dynamic_sections + ["education", "skills"]

    return SelectedResume(
        profile=resume_data.profile,
        summary=resume_data.profile.summary,
        experiences=experiences,
        projects=projects,
        skill_categories=skill_categories,
        certifications=certifications,
        education=resume_data.education,
        section_order=section_order,
        match_score=overall_score,
    )
