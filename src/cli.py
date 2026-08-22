"""CLI entry point for the resume builder."""

from pathlib import Path

import click

from filters import apply_filters, filter_bullets
from models import ExperienceBullet
from parser import load_resume_data
from pdf_generator import generate_pdf
from scorer import score_resume
from selector import SelectedResume, select_generic, select_targeted

DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


@click.group()
@click.option(
    "--data-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to YAML data directory. Defaults to ./data/",
)
@click.pass_context
def main(ctx, data_dir: Path | None):
    """ATS-optimized resume builder from structured YAML career data."""
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir or DEFAULT_DATA_DIR


@main.command()
@click.option(
    "--job-description", "-jd",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to a job description text file for targeted resume generation.",
)
@click.option(
    "--job-description-text", "-jdt",
    type=str,
    default=None,
    help="Inline job description text for targeted resume generation.",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output PDF file path. Defaults to output/resume.pdf",
)
@click.option(
    "--filter/--no-filter",
    default=True,
    help="Apply content filters to sanitize output. Enabled by default.",
)
@click.option(
    "--strict-filter",
    is_flag=True,
    default=False,
    help="Automatically redact filtered content instead of just warning.",
)
@click.option(
    "--rank-experience/--preserve-experience-order",
    default=False,
    help="In targeted mode, rank experiences by relevance instead of keeping YAML order.",
)
@click.option(
    "--email",
    type=str,
    default=None,
    help="Email address to include in the resume header (avoids storing in data files).",
)
@click.option(
    "--phone",
    type=str,
    default=None,
    help="Phone number to include in the resume header (avoids storing in data files).",
)
@click.pass_context
def generate(ctx, job_description: Path | None, job_description_text: str | None, output: Path | None, filter: bool, strict_filter: bool, rank_experience: bool, email: str | None, phone: str | None):
    """Generate an ATS-optimized PDF resume."""
    data_dir = ctx.obj["data_dir"]
    output_path = output or DEFAULT_OUTPUT_DIR / "resume.pdf"

    click.echo(f"Loading career data from {data_dir}...")
    resume_data = load_resume_data(data_dir)

    # Override contact info from CLI flags
    if email:
        resume_data.profile.email = email
    if phone:
        resume_data.profile.phone = phone

    # Determine if we're doing targeted or generic generation
    jd_text = None
    if job_description:
        jd_text = job_description.read_text(encoding="utf-8")
    elif job_description_text:
        jd_text = job_description_text

    if jd_text:
        click.echo("Scoring content against job description...")
        scored = score_resume(resume_data, jd_text)
        click.echo(f"Overall match score: {scored['overall_score']:.1%}")
        click.echo(f"Top JD keywords: {', '.join(scored['jd_keywords'][:15])}")

        click.echo("Selecting and ranking content...")
        selected = select_targeted(resume_data, scored, rank_experiences=rank_experience)
    else:
        click.echo("No job description provided — generating generic resume.")
        selected = select_generic(resume_data)
        scored = None

    # Apply content filters
    if filter:
        selected = _apply_content_filters(selected, strict=strict_filter)

    click.echo(f"Generating PDF at {output_path}...")
    generate_pdf(selected, output_path)
    click.echo(f"Done! Resume saved to {output_path}")

    if selected.match_score is not None:
        click.echo(f"\n{'='*40}")
        click.echo(f"  ATS Match Score: {selected.match_score:.1%}")
        click.echo(f"{'='*40}")

        top_skills = sorted(scored['scored_skills'], key=lambda x: x[2], reverse=True)
        top_skills = [(cat, skill, s) for cat, skill, s in top_skills if s > 0][:10]
        if top_skills:
            click.echo(f"\nTop Matching Skills:")
            for cat, skill, s in top_skills:
                click.echo(f"  [{min(s, 1.0):.0%}] {skill.name} ({cat})")

        if selected.match_score < 0.5:
            _print_low_score_recommendations(scored, resume_data)
    else:
        click.echo("\n(No ATS score — provide a job description with -jd to get a match score)")


@main.command()
@click.option(
    "--job-description", "-jd",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to a job description text file.",
)
@click.option(
    "--job-description-text", "-jdt",
    type=str,
    default=None,
    help="Inline job description text.",
)
@click.pass_context
def score(ctx, job_description: Path | None, job_description_text: str | None):
    """Show ATS match score for your resume against a job description."""
    data_dir = ctx.obj["data_dir"]

    if not job_description and not job_description_text:
        click.echo("Error: Provide a job description with --job-description or --job-description-text", err=True)
        raise SystemExit(1)

    resume_data = load_resume_data(data_dir)

    jd_text = ""
    if job_description:
        jd_text = job_description.read_text()
    elif job_description_text:
        jd_text = job_description_text

    click.echo("Scoring resume against job description...")
    scored = score_resume(resume_data, jd_text)

    click.echo(f"\n{'='*50}")
    click.echo(f"  ATS MATCH SCORE: {scored['overall_score']:.1%}")
    click.echo(f"{'='*50}\n")

    # Show top keywords found
    click.echo(f"Top JD Keywords Extracted ({len(scored['jd_keywords'])} total):")
    for kw in scored['jd_keywords'][:20]:
        click.echo(f"  - {kw}")

    # Show top matching skills
    click.echo(f"\nTop Matching Skills:")
    top_skills = sorted(scored['scored_skills'], key=lambda x: x[2], reverse=True)[:10]
    for cat, skill, s in top_skills:
        if s > 0:
            display_score = min(s, 1.0)
            click.echo(f"  [{display_score:.0%}] {skill.name} ({cat})")

    # Show experience ranking
    click.echo(f"\nExperience Relevance Ranking:")
    for exp, s, _ in sorted(scored['scored_experiences'], key=lambda x: x[1], reverse=True):
        click.echo(f"  [{s:.0%}] {exp.role} @ {exp.company}")


@main.command()
@click.pass_context
def lint(ctx):
    """Check resume data for content filter violations without generating a PDF."""
    data_dir = ctx.obj["data_dir"]
    resume_data = load_resume_data(data_dir)

    total_violations = 0
    click.echo("Scanning experience bullets for filter violations...\n")

    for exp in resume_data.experiences:
        exp_violations = []
        for bullet in exp.bullets:
            result = apply_filters(bullet.text)
            if result.violations:
                exp_violations.extend(
                    (bullet.text[:60], v) for v in result.violations
                )

        if exp_violations:
            click.echo(click.style(f"  {exp.role} @ {exp.company}", fg="yellow", bold=True))
            for bullet_preview, v in exp_violations:
                click.echo(f"    [{v.rule}] \"{v.matched_text}\"")
                click.echo(click.style(f"      → {v.suggestion}", fg="cyan"))
                total_violations += 1
            click.echo()

    # Also check summary
    if resume_data.profile.summary:
        result = apply_filters(resume_data.profile.summary)
        if result.violations:
            click.echo(click.style("  Profile Summary", fg="yellow", bold=True))
            for v in result.violations:
                click.echo(f"    [{v.rule}] \"{v.matched_text}\"")
                click.echo(click.style(f"      → {v.suggestion}", fg="cyan"))
                total_violations += 1
            click.echo()

    if total_violations == 0:
        click.echo(click.style("✓ No filter violations found!", fg="green"))
    else:
        click.echo(click.style(f"⚠ Found {total_violations} violation(s). Fix in data/ or use --strict-filter to auto-redact.", fg="yellow"))

    raise SystemExit(1 if total_violations > 0 else 0)


def _apply_content_filters(selected: SelectedResume, strict: bool = False) -> SelectedResume:
    """Apply content filters to selected resume and report violations."""
    total_violations = 0

    # Filter experience bullets
    filtered_experiences = []
    for exp, bullets in selected.experiences:
        results = filter_bullets(bullets, strict=strict)
        filtered_bullets = []
        for new_bullet, violations in results:
            if violations:
                total_violations += len(violations)
                if not strict:
                    for v in violations:
                        click.echo(
                            click.style(f"  ⚠ [{v.rule}] ", fg="yellow")
                            + f'"{v.matched_text}" in {exp.company}'
                        )
            filtered_bullets.append(new_bullet)
        filtered_experiences.append((exp, filtered_bullets))

    # Filter summary
    filtered_summary = selected.summary
    if selected.summary:
        result = apply_filters(selected.summary, strict=strict)
        if result.violations:
            total_violations += len(result.violations)
            if not strict:
                for v in result.violations:
                    click.echo(
                        click.style(f"  ⚠ [{v.rule}] ", fg="yellow")
                        + f'"{v.matched_text}" in summary'
                    )
            filtered_summary = result.filtered

    if total_violations > 0:
        mode = "auto-redacted" if strict else "warnings (use --strict-filter to redact)"
        click.echo(f"  Content filters: {total_violations} violation(s) — {mode}")

    return SelectedResume(
        profile=selected.profile,
        summary=filtered_summary,
        experiences=filtered_experiences,
        skill_categories=selected.skill_categories,
        certifications=selected.certifications,
        education=selected.education,
        section_order=selected.section_order,
        match_score=selected.match_score,
    )


def _print_low_score_recommendations(scored: dict, resume_data) -> None:
    """Print actionable recommendations when ATS score is low."""
    click.echo(click.style("\n⚠  Low ATS match. Recommendations:", fg="yellow", bold=True))

    # Find missing keywords (JD keywords not matched by any skill or bullet)
    jd_keywords = scored["jd_keywords"]
    all_skill_names = set()
    for cat in resume_data.skill_categories:
        for skill in cat.skills:
            all_skill_names.add(skill.name.lower())
            for alias in skill.aliases:
                all_skill_names.add(alias.lower())

    all_resume_text = " ".join(filter(None, [
        resume_data.profile.headline,
        resume_data.profile.summary,
        *[exp.role for exp in resume_data.experiences],
        *[exp.description or "" for exp in resume_data.experiences],
        *[b.text for exp in resume_data.experiences for b in exp.bullets],
    ])).lower()

    missing_keywords = []
    for kw in jd_keywords[:25]:
        kw_lower = kw.lower()
        in_skills = any(kw_lower in name for name in all_skill_names)
        in_bullets = kw_lower in all_resume_text
        if not in_skills and not in_bullets:
            missing_keywords.append(kw)

    if missing_keywords:
        click.echo(f"\n  Missing JD keywords not found in your data:")
        click.echo(click.style(f"    {', '.join(missing_keywords[:15])}", fg="red"))
        click.echo(f"    → Add these to skills.yaml (with aliases) or update experience bullets")

    # Find weakly matched skills (in JD but scored low)
    weak_skills = [
        (skill.name, score)
        for _, skill, score in scored["scored_skills"]
        if 0 < score < 0.5
    ]
    if weak_skills:
        click.echo(f"\n  Weak skill matches (present but low relevance):")
        for name, s in sorted(weak_skills, key=lambda x: x[1]):
            click.echo(click.style(f"    {name}", fg="yellow") + f" ({s:.0%})")
        click.echo(f"    → Add keyword aliases or strengthen related experience bullets")

    # General tips
    click.echo(f"\n  General tips:")
    click.echo(f"    - Tailor your summary to emphasize keywords from the job description")
    click.echo(f"    - Ensure certifications align with role requirements")
    click.echo(f"    - Add relevant keyword aliases in skills.yaml for better matching")


if __name__ == "__main__":
    main()
