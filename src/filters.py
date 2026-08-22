"""Content filters for resume output.

Applies rules to sanitize bullet text before PDF generation.
Rules detect and warn/redact content that violates ATS or confidentiality guidelines.
"""

import re
from dataclasses import dataclass, field

from resume_builder.models import ExperienceBullet


@dataclass
class FilterViolation:
    """A detected filter violation in a bullet."""

    rule: str
    matched_text: str
    suggestion: str


@dataclass
class FilterResult:
    """Result of applying filters to a bullet."""

    original: str
    filtered: str
    violations: list[FilterViolation] = field(default_factory=list)


# Pattern-based filters: (rule_name, regex_pattern, suggestion)
PATTERN_FILTERS: list[tuple[str, str, str]] = [
    # Code metrics (file counts, LOC)
    (
        "no-code-metrics",
        r"\d+\+?\s*(?:source|test)\s*files",
        "Remove code/file count metrics",
    ),
    (
        "no-code-metrics",
        r"\d+[,\d]*\+?\s*(?:lines?\s*of\s*code|LOC)",
        "Remove lines-of-code metrics",
    ),
    # Workflow implementation details (N jobs, N-stage)
    (
        "no-workflow-internals",
        r"\d+\s*(?:distinct\s*)?(?:workflow\s*)?jobs?\b",
        "Describe outcome instead of job count (e.g., 'simplified orchestration')",
    ),
    (
        "no-workflow-internals",
        r"\d+-stage\s*(?:CI/?CD\s*)?pipeline",
        "Describe outcome instead of stage count (e.g., 'automated validation and publishing')",
    ),
    # Specific internal design patterns
    (
        "no-design-patterns",
        r"\b(?:dependency\s*inversion|producer/?consumer\s*pattern|observer\s*pattern|factory\s*pattern|strategy\s*pattern|mediator\s*pattern)\b",
        "Describe by purpose, not internal design pattern name",
    ),
    # Specific internal library choices (non-mainstream)
    (
        "no-internal-libraries",
        r"\b(?:Effect(?:\s+(?:for|library|framework))?|Commander|HotChocolate|MediatR|Zod|Octokit)\b",
        "Remove specific internal library names — describe what the tool does instead",
    ),
    # Specific agent configuration names
    (
        "no-agent-internals",
        r"\b(?:BDD\s*Specialist|API\s*Specialist|TDD\s*(?:Red/?Green/?Blue|workflow)\s*(?:agent|specialist)?)\b",
        "Use generic terms like 'Custom Agents' instead of specific agent names",
    ),
    # Exact file-type listings for configurations
    (
        "no-config-exhaustive-lists",
        r"\.github/(?:agents|prompts|instructions|skills)/",
        "Simplify configuration references — mention categories, not specific file paths",
    ),
]

# Keywords/phrases that indicate describing internal design rather than purpose
DESIGN_LANGUAGE_PATTERNS: list[tuple[str, str]] = [
    (r"\bcomposable\s*resources\b", "Describe the solution's purpose instead"),
    (r"\borchestration\s*internals\b", "Describe outcome, not orchestration details"),
    (r"\blayered\s*(?:architecture|composition)\s*pattern\b", "Describe what the tool does"),
    (r"\bEffect-based\s*dependency\s*injection\b", "Describe the tool's purpose"),
]

# Patterns for exact percentages that should be generalized
PERCENTAGE_CONTEXT_PATTERNS: list[tuple[str, str, str]] = [
    # Feature adoption percentages (internal metrics)
    (
        r"(\d{2,3})%\s*(?:of\s*(?:all\s*)?demos?\s*(?:created|used))",
        "majority of demos",
        "Use qualitative terms for internal adoption (e.g., 'majority of demos')",
    ),
]

# User count patterns with org breakdown
USER_COUNT_PATTERNS: list[tuple[str, str]] = [
    (
        r"\d+\s*unique\s*users\s*across\s*(?:GitHub|Microsoft|Partners|[\w,\s]+(?:and|&)\s*\w+)",
        "Generalize user counts (e.g., '900+ users across the organization')",
    ),
]


def apply_filters(text: str, strict: bool = False) -> FilterResult:
    """Apply all content filters to a text string.

    Args:
        text: The bullet text to filter.
        strict: If True, automatically redact matched patterns. If False, only report violations.

    Returns:
        FilterResult with original text, filtered text, and any violations found.
    """
    violations: list[FilterViolation] = []
    filtered = text

    # Apply pattern-based filters
    for rule_name, pattern, suggestion in PATTERN_FILTERS:
        matches = re.finditer(pattern, filtered, re.IGNORECASE)
        for match in matches:
            violations.append(FilterViolation(
                rule=rule_name,
                matched_text=match.group(),
                suggestion=suggestion,
            ))
            if strict:
                filtered = filtered[:match.start()] + filtered[match.end():]

    # Apply design language patterns
    for pattern, suggestion in DESIGN_LANGUAGE_PATTERNS:
        matches = re.finditer(pattern, filtered, re.IGNORECASE)
        for match in matches:
            violations.append(FilterViolation(
                rule="no-design-language",
                matched_text=match.group(),
                suggestion=suggestion,
            ))

    # Apply percentage context patterns
    for pattern, replacement, suggestion in PERCENTAGE_CONTEXT_PATTERNS:
        matches = re.finditer(pattern, filtered, re.IGNORECASE)
        for match in matches:
            violations.append(FilterViolation(
                rule="no-exact-adoption-percentages",
                matched_text=match.group(),
                suggestion=suggestion,
            ))
            if strict:
                filtered = filtered[:match.start()] + replacement + filtered[match.end():]

    # Apply user count patterns
    for pattern, suggestion in USER_COUNT_PATTERNS:
        matches = re.finditer(pattern, filtered, re.IGNORECASE)
        for match in matches:
            violations.append(FilterViolation(
                rule="no-exact-user-breakdown",
                matched_text=match.group(),
                suggestion=suggestion,
            ))

    # Clean up double spaces from redactions
    if strict:
        filtered = re.sub(r"  +", " ", filtered).strip()
        # Remove dangling connectors
        filtered = re.sub(r"\s*—\s*$", "", filtered)
        filtered = re.sub(r"^\s*—\s*", "", filtered)

    return FilterResult(original=text, filtered=filtered, violations=violations)


def filter_bullets(
    bullets: list[ExperienceBullet], strict: bool = False
) -> list[tuple[ExperienceBullet, list[FilterViolation]]]:
    """Apply filters to a list of experience bullets.

    Returns bullets (possibly modified if strict=True) paired with their violations.
    """
    results = []
    for bullet in bullets:
        result = apply_filters(bullet.text, strict=strict)
        if strict and result.filtered != result.original:
            new_bullet = ExperienceBullet(text=result.filtered, keywords=bullet.keywords)
        else:
            new_bullet = bullet
        results.append((new_bullet, result.violations))
    return results
