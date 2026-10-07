# ATS Resume Builder

> CLI tool that generates ATS-optimized PDF resumes from structured YAML career data. Optionally accepts a job description to tailor content using TF-IDF scoring (no LLM required).

## Quick Start

On Linux or MacOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows:

```bash
python -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install -e ".[dev]"
```

## Usage

```bash
# Generate a generic resume (all experience, default ordering)
python -m resume_builder generate

# Generate a targeted resume for a specific job description
python -m resume_builder generate --job-description path/to/jd.txt

# Generate with inline JD text
python -m resume_builder generate --job-description-text "We are looking for..."

# Pass contact info at runtime (avoids storing sensitive data in files)
python -m resume_builder generate --email "you@example.com" --phone "+55 99 99999-9999"

# Specify custom data directory or output path
python -m resume_builder --data-dir ./data generate --output ./my-resume.pdf
```

When a job description is passed, `generate` also prints an ATS match score
after the PDF is written — computed by extracting the text back out of the
*generated PDF* (not the source YAML) and simulating how a real ATS parser
reads it: detecting section headers and entry boundaries from formatting
cues alone, the same way tools like Workday or Greenhouse do, rather than
trusting our own data model's field names. Without a job description,
`generate` produces the PDF with no score.

## How It Works

1. **Reads** structured YAML career data from `data/` (profile, experiences, skills, certifications, education)
2. **Optionally scores** content against a job description (TF-IDF cosine similarity + keyword matching) to select and rank what goes into the resume
3. **Selects and ranks** the most relevant skills, experience bullets, and certifications
4. **Generates** a clean, ATS-friendly PDF (single-column, standard fonts, no graphics)
5. **If a job description was given**, re-extracts the text from the generated PDF and scores *that* — the number reported to you — by detecting sections/entries the way a real ATS parser would (bold/uppercase or fuzzy-matched headers, vertical-gap/bold-line entry boundaries), not by reading the YAML's known field names

## Data Format

Edit your career data in `data/`:

- `profile.yaml` — Name, contact info, headline, summary
- `experiences.yaml` — Work history with bullet points and per-role technologies used (rendered in the PDF and used for scoring)
- `projects.yaml` — Optional. Projects with bullet points and per-project technologies used, like experiences but with no company/role and year-only dates (omit the file entirely if you have none)
- `skills.yaml` — Skills grouped by category with years of experience
- `certifications.yaml` — Professional certifications
- `education.yaml` — Degrees and institutions

## ATS Optimization Strategies Applied

- Single-column layout with standard fonts (Helvetica)
- Standard section headings (Professional Summary, Professional Experience, Technical Skills, etc.)
- No graphics, tables, or images
- Keywords from job description mirrored in content selection
- Skills ordered by relevance to target role
- Experience bullets ranked and filtered by keyword match score

## Try It With the Example Data

The `example/` folder contains a fictional career profile plus a sample job
description, so you can try the CLI without setting up your own data first:

```bash
# Generate a generic resume from the example data
python -m resume_builder --data-dir example generate --output ./example-resume.pdf

# Generate a resume tailored to the example job description (also prints
# the ATS match score, computed from the generated PDF)
python -m resume_builder --data-dir example generate --job-description example/job-description.txt --output example/example-resume-tailored.pdf
```

## Running Tests

```bash
python -m pytest tests/ -v
```
