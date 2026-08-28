# ATS Resume Builder

> CLI tool that generates ATS-optimized PDF resumes from structured YAML career data. Optionally accepts a job description to tailor content using TF-IDF scoring (no LLM required).

## Quick Start

On Linux or MacOS:

```bash
python3.14 -m venv .venv
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
python -m cli generate

# Generate a targeted resume for a specific job description
python -m cli generate --job-description path/to/jd.txt

# Generate with inline JD text
python -m cli generate --job-description-text "We are looking for..."

# Pass contact info at runtime (avoids storing sensitive data in files)
python -m cli generate --email "you@example.com" --phone "+55 99 99999-9999"

# Show ATS match score against a job description
python -m cli score --job-description path/to/jd.txt

# Specify custom data directory or output path
python -m cli --data-dir ./data generate --output ./my-resume.pdf
```

## How It Works

1. **Reads** structured YAML career data from `data/` (profile, experiences, skills, certifications, education)
2. **Optionally scores** content against a job description using TF-IDF cosine similarity + keyword matching
3. **Selects and ranks** the most relevant skills, experience bullets, and certifications
4. **Generates** a clean, ATS-friendly PDF (single-column, standard fonts, no graphics)

## Data Format

Edit your career data in `data/`:

- `profile.yaml` — Name, contact info, headline, summary
- `experiences.yaml` — Work history with bullet points and per-role keywords (rendered in the PDF and used for scoring)
- `projects.yaml` — Optional. Projects with bullet points and per-project keywords, like experiences but with no company/role and year-only dates (omit the file entirely if you have none)
- `skills.yaml` — Skills grouped by category with years of experience and aliases
- `certifications.yaml` — Professional certifications
- `education.yaml` — Degrees and institutions

## ATS Optimization Strategies Applied

- Single-column layout with standard fonts (Helvetica)
- Standard section headings (Professional Summary, Professional Experience, Technical Skills, etc.)
- No graphics, tables, or images
- Keywords from job description mirrored in content selection
- Skills ordered by relevance to target role
- Experience bullets ranked and filtered by keyword match score
- Both full names and acronyms included via skill aliases

## Try It With the Example Data

The `example/` folder contains a fictional career profile plus a sample job
description, so you can try the CLI without setting up your own data first:

```bash
# Generate a generic resume from the example data
python -m cli --data-dir example generate --output ./example-resume.pdf

# Generate a resume tailored to the example job description
python -m cli --data-dir example generate --job-description example/job-description.txt --output example/example-resume-tailored.pdf

# Score the example profile against the example job description
python -m cli --data-dir example score --job-description example/job-description.txt
```

## Running Tests

```bash
python -m pytest tests/ -v
```
