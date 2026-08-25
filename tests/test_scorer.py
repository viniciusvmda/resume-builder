"""Tests for the scoring engine."""

import pytest

from models import (
    Certification,
    Experience,
    ExperienceBullet,
    Profile,
    ResumeData,
    Skill,
    SkillCategory,
)
from scorer import (
    classify_jd_keywords,
    extract_keywords,
    extract_years_requirements,
    fuzzy_match_ok,
    score_bullet,
    score_certification,
    score_experience,
    score_keyword_match,
    score_keyword_relevance,
    score_resume,
    score_skill,
    score_text_similarity,
    score_years_requirement,
)


class TestExtractKeywords:
    def test_extracts_relevant_terms(self):
        jd = "We need a Senior Cloud Architect with Azure, Terraform, and Kubernetes experience."
        keywords = extract_keywords(jd)
        assert len(keywords) > 0
        # Should find tech terms
        lower_kws = [kw.lower() for kw in keywords]
        assert any("azure" in kw for kw in lower_kws)
        assert any("terraform" in kw for kw in lower_kws)

    def test_empty_text_returns_empty(self):
        assert extract_keywords("") == []

    def test_short_text_returns_empty(self):
        assert extract_keywords("hi") == []

    def test_single_char_language_extracted(self):
        jd = "We need someone skilled in C and R for statistical computing work."
        keywords = [kw.lower() for kw in extract_keywords(jd)]
        assert "c" in keywords
        assert "r" in keywords


class TestScoreTextSimilarity:
    def test_identical_texts_high_score(self):
        text = "Experience with Azure cloud architecture and Terraform infrastructure"
        score = score_text_similarity(text, text)
        assert score > 0.9

    def test_unrelated_texts_low_score(self):
        text = "I enjoy cooking pasta and baking bread"
        jd = "Senior cloud architect with Kubernetes and Terraform"
        score = score_text_similarity(text, jd)
        assert score < 0.1

    def test_empty_text_returns_zero(self):
        assert score_text_similarity("", "some job description") == 0.0
        assert score_text_similarity("some text", "") == 0.0


class TestScoreKeywordMatch:
    def test_all_keywords_present(self):
        text = "I have experience with Azure, Terraform, and Kubernetes"
        keywords = ["azure", "terraform", "kubernetes"]
        score = score_keyword_match(text, keywords)
        assert score == 1.0

    def test_no_keywords_present(self):
        text = "I enjoy cooking and gardening"
        keywords = ["azure", "terraform", "kubernetes"]
        score = score_keyword_match(text, keywords)
        assert score < 0.3

    def test_partial_match(self):
        text = "I have experience with Azure and Docker"
        keywords = ["azure", "terraform", "docker"]
        score = score_keyword_match(text, keywords)
        assert 0.5 <= score <= 1.0

    def test_empty_keywords_returns_zero(self):
        assert score_keyword_match("some text", []) == 0.0

    def test_negated_keyword_not_counted(self):
        text = "We have no Kubernetes experience on this team"
        keywords = ["kubernetes"]
        score = score_keyword_match(text, keywords)
        assert score == 0.0

    def test_negation_window_limited(self):
        # negation cue is far before the match, well outside the window
        text = (
            "We used to think there was no chance of success but after "
            "years of hard work the team eventually adopted Kubernetes fully"
        )
        keywords = ["kubernetes"]
        score = score_keyword_match(text, keywords)
        assert score == 1.0

    def test_required_keyword_weighted_higher_than_preferred(self):
        jd_classification = {"required": {"python"}, "preferred": {"java"}}
        score_required_only = score_keyword_match("Python", ["python"], jd_classification)
        score_preferred_only = score_keyword_match("Java", ["java"], jd_classification)
        assert score_required_only == 1.0
        assert score_preferred_only == 1.0
        # Weighted combined score should favor required coverage
        combined_missing_required = score_keyword_match(
            "Java", ["python", "java"], jd_classification
        )
        combined_missing_preferred = score_keyword_match(
            "Python", ["python", "java"], jd_classification
        )
        assert combined_missing_preferred > combined_missing_required


class TestScoreSkill:
    def test_exact_match_in_jd(self):
        skill = Skill(name="Terraform", years=5)
        jd = "We need someone with Terraform experience"
        score = score_skill(skill, ["terraform"], jd)
        assert score == 1.0

    def test_alias_match(self):
        skill = Skill(name="Amazon Web Services (AWS)", years=7, aliases=["AWS"])
        jd = "AWS experience required"
        score = score_skill(skill, ["aws"], jd)
        assert score == 1.0

    def test_no_match(self):
        skill = Skill(name="Cooking", years=10)
        jd = "We need a cloud architect with Azure"
        score = score_skill(skill, ["azure", "cloud"], jd)
        assert score < 0.5

    def test_negated_skill_not_credited(self):
        skill = Skill(name="Kubernetes", years=5)
        jd = "This role requires no prior Kubernetes experience"
        score = score_skill(skill, ["kubernetes"], jd)
        assert score == 0.0

    @pytest.mark.parametrize("years", [10, 50, 1000])
    def test_score_skill_never_exceeds_one(self, years):
        skill = Skill(name="Terraform", years=years)
        jd = "We need someone with Terraform experience"
        score = score_skill(skill, ["terraform"], jd)
        assert 0.0 <= score <= 1.0


class TestScoreYearsRequirement:
    def test_extract_years_requirements_patterns(self):
        jd = "5+ years of Python required. 3-5 years Kubernetes experience preferred."
        reqs = extract_years_requirements(jd)
        assert len(reqs) == 2
        assert reqs[0].min_years == 5
        assert "python" in reqs[0].skill_hint.lower()
        assert reqs[1].min_years == 3
        assert reqs[1].max_years == 5

    def test_score_years_requirement_penalizes_shortfall(self):
        skill = Skill(name="Python", years=1)
        reqs = extract_years_requirements("5+ years of Python required")
        multiplier = score_years_requirement(skill, reqs)
        assert multiplier < 1.0

    def test_score_years_requirement_neutral_when_no_requirement(self):
        skill = Skill(name="Ruby", years=1)
        reqs = extract_years_requirements("5+ years of Python required")
        multiplier = score_years_requirement(skill, reqs)
        assert multiplier == 1.0

    def test_score_years_requirement_neutral_with_no_requirements(self):
        skill = Skill(name="Python", years=1)
        assert score_years_requirement(skill, []) == 1.0
        assert score_years_requirement(skill, None) == 1.0


class TestClassifyJdKeywords:
    def test_required_vs_preferred(self):
        jd = "Python is required. Kubernetes experience is preferred."
        keywords = ["python", "kubernetes"]
        classification = classify_jd_keywords(jd, keywords)
        assert "python" in classification["required"]
        assert "kubernetes" in classification["preferred"]

    def test_unclassified_keyword_falls_to_general(self):
        jd = "We use Python and Java daily."
        keywords = ["python", "java"]
        classification = classify_jd_keywords(jd, keywords)
        assert classification["required"] == set()
        assert classification["preferred"] == set()
        assert {"python", "java"} <= classification["general"]


class TestFuzzyMatchOk:
    def test_short_string_no_fuzzy_match(self):
        matched, _ = fuzzy_match_ok("r", "ruby")
        assert matched is False

    def test_short_string_exact_still_matches(self):
        matched, score = fuzzy_match_ok("go", "go")
        assert matched is True
        assert score == 1.0

    def test_fuzzy_threshold_scales_with_length(self):
        # "java" vs "jave" (1 char off, 4 chars) needs the stricter 92 threshold
        matched, _ = fuzzy_match_ok("java", "jave")
        assert matched is False


class TestScoreKeywordRelevance:
    def test_empty_keywords_returns_zero(self):
        assert score_keyword_relevance("some text", []) == 0.0

    def test_no_match_returns_zero(self):
        score = score_keyword_relevance("I enjoy cooking", ["azure", "kubernetes"])
        assert score == 0.0

    def test_saturates_at_one(self):
        text = "Azure Terraform Kubernetes Docker AWS GCP Prometheus Grafana"
        keywords = ["azure", "terraform", "kubernetes", "docker", "aws", "gcp"]
        score = score_keyword_relevance(text, keywords)
        assert score == 1.0

    def test_more_high_value_matches_scores_higher(self):
        keywords = ["azure", "terraform", "kubernetes"]
        rich = score_keyword_relevance("Azure Terraform Kubernetes expert", keywords)
        thin = score_keyword_relevance("Azure specialist", keywords)
        assert rich > thin

    def test_score_independent_of_unrelated_keyword_pool_size(self):
        # A text's score for the keywords it actually matches must not
        # change just because the candidate keyword list also contains many
        # unrelated terms (regression: this is what caused a broad,
        # specific experience to score *worse* than a narrow generic one
        # under a per-item ratio/denominator design).
        keywords_small = ["kafka", "go"]
        keywords_large = keywords_small + [f"unrelated{i}" for i in range(50)]
        text = "Built Kafka consumers in Go"
        assert score_keyword_relevance(text, keywords_small) == score_keyword_relevance(
            text, keywords_large
        )


class TestScoreBullet:
    def test_relevant_bullet_scores_high(self):
        bullet = ExperienceBullet(
            text="Designed hub-and-spoke network topology with Azure Firewall and Private Endpoints",
        )
        jd = "Design hub-and-spoke network architectures with Azure networking services"
        jd_keywords = ["azure", "hub-and-spoke", "networking", "network"]
        score = score_bullet(bullet, jd_keywords, jd)
        assert score > 0.3

    def test_irrelevant_bullet_scores_low(self):
        bullet = ExperienceBullet(
            text="Built a content management platform for press releases",
        )
        jd = "Cloud architect with Azure, Terraform, and Kubernetes"
        jd_keywords = ["azure", "terraform", "kubernetes", "cloud"]
        score = score_bullet(bullet, jd_keywords, jd)
        assert score < 0.2

    def test_score_bullet_never_exceeds_one(self):
        bullet = ExperienceBullet(text="Azure Terraform Kubernetes Azure Terraform Kubernetes")
        jd = "Cloud architect with Azure, Terraform, and Kubernetes"
        jd_keywords = ["azure", "terraform", "kubernetes"]
        score = score_bullet(bullet, jd_keywords, jd)
        assert 0.0 <= score <= 1.0


class TestScoreExperience:
    def test_role_keywords_boost_score(self):
        jd = "Cloud architect with Azure, Terraform, and Kubernetes"
        jd_keywords = ["azure", "terraform", "kubernetes", "cloud"]
        base = Experience(
            company="Acme",
            role="Engineer",
            start_date="Jan 2020",
            bullets=[ExperienceBullet(text="Did some unrelated work")],
        )
        with_keywords = Experience(
            company="Acme",
            role="Engineer",
            start_date="Jan 2020",
            keywords=["Azure", "Terraform", "Kubernetes"],
            bullets=[ExperienceBullet(text="Did some unrelated work")],
        )
        assert score_experience(with_keywords, jd_keywords, jd) > score_experience(
            base, jd_keywords, jd
        )

    def test_score_experience_never_exceeds_one(self):
        jd = "Cloud architect with Azure, Terraform, and Kubernetes"
        jd_keywords = ["azure", "terraform", "kubernetes", "cloud"]
        exp = Experience(
            company="Acme",
            role="Cloud Architect",
            start_date="Jan 2020",
            description="Cloud architect with Azure, Terraform, and Kubernetes",
            keywords=["Azure", "Terraform", "Kubernetes"],
            bullets=[
                ExperienceBullet(text="Cloud architect with Azure, Terraform, and Kubernetes")
            ],
        )
        score = score_experience(exp, jd_keywords, jd)
        assert 0.0 <= score <= 1.0

    def test_broad_specific_match_outranks_narrow_generic_match(self):
        # Regression: a per-item denominator scoped to "keywords found in
        # this experience" made a narrow, generic-titled experience easier
        # to satisfy than one that genuinely covers many specific JD terms.
        jd = (
            "Senior Backend Engineer. Requirements: Go, Kafka, PostgreSQL, "
            "Kubernetes, Docker, Prometheus, Grafana, mentoring engineers."
        )
        jd_keywords = [
            "go", "kafka", "postgresql", "kubernetes", "docker",
            "prometheus", "grafana", "mentoring", "engineers", "backend",
        ]
        broad_specific = Experience(
            company="Acme",
            role="Senior Backend Engineer",
            start_date="Jan 2020",
            bullets=[
                ExperienceBullet(text="Built Kafka and Go services on Kubernetes with Docker"),
                ExperienceBullet(text="Ran PostgreSQL at scale and set up Prometheus and Grafana"),
                ExperienceBullet(text="Mentored engineers across the backend team"),
            ],
        )
        narrow_generic = Experience(
            company="Acme",
            role="Backend Engineer",
            start_date="Jan 2020",
            bullets=[ExperienceBullet(text="Worked on backend systems")],
        )
        assert score_experience(broad_specific, jd_keywords, jd) > score_experience(
            narrow_generic, jd_keywords, jd
        )


class TestScoreCertification:
    def test_cert_name_matches_keyword(self):
        cert = Certification(name="AWS Certified Solutions Architect")
        score = score_certification(cert, ["aws", "architect"], "AWS Solutions Architect role")
        assert score > 0.0

    def test_cert_no_match(self):
        cert = Certification(name="Certified Yoga Instructor")
        score = score_certification(cert, ["aws", "kubernetes"], "AWS Cloud role")
        assert score == 0.0

    def test_cert_bounded(self):
        cert = Certification(name="AWS Certified Solutions Architect")
        score = score_certification(cert, ["aws", "certified", "solutions", "architect"], "x")
        assert 0.0 <= score <= 1.0


def _make_resume_data() -> ResumeData:
    return ResumeData(
        profile=Profile(name="Jane Doe", summary="Cloud architect"),
        experiences=[
            Experience(
                company="Acme",
                role="Cloud Architect",
                start_date="Jan 2020",
                description="Led cloud infrastructure work with Azure and Terraform",
                bullets=[
                    ExperienceBullet(text="Designed Azure networking with Terraform"),
                ],
            )
        ],
        skill_categories=[
            SkillCategory(
                category="Cloud",
                skills=[Skill(name="Azure", years=5), Skill(name="Terraform", years=3)],
            )
        ],
        certifications=[Certification(name="Azure Solutions Architect")],
    )


class TestScoreResume:
    def test_overall_score_bounded(self):
        resume_data = _make_resume_data()
        jd = "Cloud architect with Azure and Terraform, 3+ years required."
        scored = score_resume(resume_data, jd)
        assert 0.0 <= scored["overall_score"] <= 1.0

    def test_category_scores_present_and_bounded(self):
        resume_data = _make_resume_data()
        jd = "Cloud architect with Azure and Terraform, 3+ years required."
        scored = score_resume(resume_data, jd)
        for value in scored["category_scores"].values():
            assert 0.0 <= value <= 1.0
        assert set(scored["category_scores"]) == {
            "skills",
            "experience",
            "certifications",
            "keyword_coverage",
        }

    def test_overall_score_weighted_by_category(self):
        resume_data = _make_resume_data()
        jd = "Cloud architect with Azure and Terraform, 3+ years required."
        scored = score_resume(resume_data, jd)
        cat = scored["category_scores"]
        expected = (
            cat["skills"] * 0.35
            + cat["experience"] * 0.40
            + cat["certifications"] * 0.10
            + cat["keyword_coverage"] * 0.15
        )
        assert scored["overall_score"] == pytest.approx(expected)

    def test_explanation_lists_missing_required_keywords(self):
        resume_data = _make_resume_data()
        jd = "Cloud architect with Azure, Terraform, and Kubernetes required."
        scored = score_resume(resume_data, jd)
        assert "kubernetes" in [k.lower() for k in scored["explanation"]["missing_required"]]

    def test_all_scores_within_bounds(self):
        resume_data = _make_resume_data()
        jd = "Cloud architect with Azure, Terraform, and Kubernetes required."
        scored = score_resume(resume_data, jd)
        for _, _, s in scored["scored_skills"]:
            assert 0.0 <= s <= 1.0
        for _, s, bullet_scores in scored["scored_experiences"]:
            assert 0.0 <= s <= 1.0
            for _, bs in bullet_scores:
                assert 0.0 <= bs <= 1.0
        for _, s in scored["scored_certifications"]:
            assert 0.0 <= s <= 1.0


class TestScoreBoundsProperty:
    """Regression backstop: every score_* function must stay within [0, 1]
    across a matrix of edge-case inputs."""

    @pytest.mark.parametrize(
        "text,keywords",
        [
            ("", ["azure"]),
            ("no python experience at all", ["python"]),
            ("r", ["r", "ruby"]),
            ("Azure " * 50, ["azure"]),
            ("completely unrelated text about cooking", ["kubernetes"]),
        ],
    )
    def test_score_keyword_match_bounded(self, text, keywords):
        assert 0.0 <= score_keyword_match(text, keywords) <= 1.0

    @pytest.mark.parametrize("years", [0, 1, 100])
    def test_score_skill_bounded(self, years):
        skill = Skill(name="Python", years=years)
        jd = "5+ years of Python required, no Java experience needed"
        assert 0.0 <= score_skill(skill, ["python", "java"], jd) <= 1.0
