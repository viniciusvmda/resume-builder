"""Tests for the PDF-text-based (simulated ATS) scoring path."""

from resume_builder.models import Skill
from resume_builder.pdf_parser import parse_resume_pdf
from resume_builder.scorer import (
    YearsRequirement,
    score_resume_from_pdf,
    score_years_requirement,
)

RELEVANT_JD = """
We are looking for a Senior Cloud Architect with 5+ years of experience in
Azure, Terraform, and Kubernetes. Requirements: strong background in
infrastructure as code and cost optimization.
"""

UNRELATED_JD = """
We are looking for a Pastry Chef with experience in French baking
techniques, cake decoration, and kitchen management.
"""


class TestScoreResumeFromPdf:
    def test_overall_score_bounded(self, generated_pdf_path):
        parsed = parse_resume_pdf(generated_pdf_path)
        scored = score_resume_from_pdf(parsed, RELEVANT_JD)
        assert 0.0 <= scored["overall_score"] <= 1.0

    def test_category_scores_present_and_bounded(self, generated_pdf_path):
        parsed = parse_resume_pdf(generated_pdf_path)
        scored = score_resume_from_pdf(parsed, RELEVANT_JD)
        cat_scores = scored["category_scores"]
        for key in ("skills", "experience", "certifications", "keyword_coverage"):
            assert key in cat_scores
            assert 0.0 <= cat_scores[key] <= 1.0

    def test_relevant_jd_scores_higher_than_unrelated(self, generated_pdf_path):
        parsed = parse_resume_pdf(generated_pdf_path)
        relevant_score = score_resume_from_pdf(parsed, RELEVANT_JD)["overall_score"]
        unrelated_score = score_resume_from_pdf(parsed, UNRELATED_JD)["overall_score"]
        assert relevant_score > unrelated_score

    def test_experience_entries_use_text_label_not_model_object(self, generated_pdf_path):
        parsed = parse_resume_pdf(generated_pdf_path)
        scored = score_resume_from_pdf(parsed, RELEVANT_JD)
        assert scored["scored_experiences"]
        label, score, _bullet_scores = scored["scored_experiences"][0]
        assert isinstance(label, str)
        assert isinstance(score, float)

    def test_skills_recovered_from_skills_section_text(self, generated_pdf_path):
        parsed = parse_resume_pdf(generated_pdf_path)
        scored = score_resume_from_pdf(parsed, RELEVANT_JD)
        skill_names = {skill.name for _, skill, _ in scored["scored_skills"]}
        assert any("Azure" in name or "Terraform" in name for name in skill_names)


class TestScoreYearsRequirementPenalizeUnknown:
    def test_unknown_years_penalized_by_default(self):
        skill = Skill(name="Azure", years=None)
        requirements = [YearsRequirement("azure", 5.0, None)]
        assert score_years_requirement(skill, requirements) == 0.0

    def test_unknown_years_neutral_when_penalize_unknown_false(self):
        skill = Skill(name="Azure", years=None)
        requirements = [YearsRequirement("azure", 5.0, None)]
        assert (
            score_years_requirement(skill, requirements, penalize_unknown=False)
            == 1.0
        )
