"""Tests for content filters."""

import pytest

from resume_builder.filters import apply_filters, filter_bullets
from resume_builder.models import ExperienceBullet


class TestApplyFilters:
    def test_detects_internal_libraries(self):
        text = "Built CLI with Effect for typed error handling and Commander for parsing"
        result = apply_filters(text)
        assert len(result.violations) >= 2
        rules = [v.rule for v in result.violations]
        assert "no-internal-libraries" in rules

    def test_detects_code_metrics(self):
        text = "Architected the CLI across 309+ source files and 207+ test files"
        result = apply_filters(text)
        assert len(result.violations) == 2
        assert all(v.rule == "no-code-metrics" for v in result.violations)

    def test_detects_workflow_internals(self):
        text = "Reduced provisioning from 17 distinct workflow jobs to a single job"
        result = apply_filters(text)
        assert any(v.rule == "no-workflow-internals" for v in result.violations)

    def test_detects_pipeline_stages(self):
        text = "Built a 7-stage CI/CD pipeline for automated validation"
        result = apply_filters(text)
        assert any(v.rule == "no-workflow-internals" for v in result.violations)

    def test_detects_design_patterns(self):
        text = "Used dependency inversion for composable architecture"
        result = apply_filters(text)
        assert any(v.rule == "no-design-patterns" for v in result.violations)

    def test_detects_agent_internals(self):
        text = "Built BDD Specialist and API Specialist agents"
        result = apply_filters(text)
        assert any(v.rule == "no-agent-internals" for v in result.violations)

    def test_detects_adoption_percentages(self):
        text = "reaching 73% of all demos created"
        result = apply_filters(text)
        assert any(v.rule == "no-exact-adoption-percentages" for v in result.violations)

    def test_clean_text_has_no_violations(self):
        text = "Drove a 4.5x increase in monthly demos with 80% adoption among target teams"
        result = apply_filters(text)
        assert len(result.violations) == 0

    def test_strict_mode_redacts_libraries(self):
        text = "Built CLI with Effect for typed error handling"
        result = apply_filters(text, strict=True)
        assert "Effect for" not in result.filtered

    def test_strict_mode_redacts_code_metrics(self):
        text = "spanning 309+ source files"
        result = apply_filters(text, strict=True)
        assert "309+ source files" not in result.filtered

    def test_strict_mode_replaces_adoption_pct(self):
        text = "reaching 73% of all demos created"
        result = apply_filters(text, strict=True)
        assert "majority of demos" in result.filtered

    def test_config_file_paths_detected(self):
        text = "Created .github/agents/ and .github/prompts/ with specific configs"
        result = apply_filters(text)
        assert any(v.rule == "no-config-exhaustive-lists" for v in result.violations)


class TestFilterBullets:
    def test_returns_same_length(self):
        bullets = [
            ExperienceBullet(text="Clean bullet with no issues"),
            ExperienceBullet(text="Built with Effect for error handling"),
        ]
        results = filter_bullets(bullets)
        assert len(results) == 2

    def test_strict_modifies_violating_bullets(self):
        bullets = [
            ExperienceBullet(text="Built CLI spanning 309+ source files"),
        ]
        results = filter_bullets(bullets, strict=True)
        new_bullet, violations = results[0]
        assert "309+ source files" not in new_bullet.text
        assert len(violations) > 0

    def test_non_strict_preserves_original(self):
        bullets = [
            ExperienceBullet(text="Built CLI spanning 309+ source files"),
        ]
        results = filter_bullets(bullets, strict=False)
        new_bullet, violations = results[0]
        assert "309+ source files" in new_bullet.text
        assert len(violations) > 0
