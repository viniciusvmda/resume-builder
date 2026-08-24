"""Tests for the scoring engine."""


from models import Experience, ExperienceBullet, Skill
from scorer import (
    extract_keywords,
    score_bullet,
    score_experience,
    score_keyword_match,
    score_skill,
    score_text_similarity,
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


class TestScoreSkill:
    def test_exact_match_in_jd(self):
        skill = Skill(name="Terraform", years=5)
        jd = "We need someone with Terraform experience"
        score = score_skill(skill, ["terraform"], jd)
        assert score >= 1.0

    def test_alias_match(self):
        skill = Skill(name="Amazon Web Services (AWS)", years=7, aliases=["AWS"])
        jd = "AWS experience required"
        score = score_skill(skill, ["aws"], jd)
        assert score >= 1.0

    def test_no_match(self):
        skill = Skill(name="Cooking", years=10)
        jd = "We need a cloud architect with Azure"
        score = score_skill(skill, ["azure", "cloud"], jd)
        assert score < 0.5


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
