"""Tests for the YAML loader."""

import pytest

from parser import load_projects, load_resume_data


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "profile.yaml").write_text("name: Jane Doe\n")
    (tmp_path / "experiences.yaml").write_text("[]\n")
    (tmp_path / "skills.yaml").write_text("[]\n")
    (tmp_path / "certifications.yaml").write_text("[]\n")
    (tmp_path / "education.yaml").write_text("[]\n")
    return tmp_path


class TestLoadProjects:
    def test_missing_file_returns_empty_list(self, data_dir):
        assert load_projects(data_dir) == []

    def test_loads_string_and_dict_bullets(self, data_dir):
        (data_dir / "projects.yaml").write_text(
            """
- name: Side Project
  start_year: "2022"
  end_year: "2023"
  bullets:
    - "Plain string bullet"
    - text: "Dict-form bullet"
"""
        )
        projects = load_projects(data_dir)
        assert len(projects) == 1
        assert [b.text for b in projects[0].bullets] == [
            "Plain string bullet",
            "Dict-form bullet",
        ]

    def test_coerces_unquoted_int_years_to_str(self, data_dir):
        (data_dir / "projects.yaml").write_text(
            """
- name: Side Project
  start_year: 2022
  end_year: 2023
"""
        )
        projects = load_projects(data_dir)
        assert projects[0].start_year == "2022"
        assert projects[0].end_year == "2023"

    def test_end_year_defaults_to_present(self, data_dir):
        (data_dir / "projects.yaml").write_text(
            """
- name: Side Project
  start_year: "2022"
"""
        )
        projects = load_projects(data_dir)
        assert projects[0].end_year == "Present"


class TestLoadResumeData:
    def test_projects_empty_when_file_absent(self, data_dir):
        resume_data = load_resume_data(data_dir)
        assert resume_data.projects == []

    def test_projects_loaded_when_file_present(self, data_dir):
        (data_dir / "projects.yaml").write_text(
            """
- name: Side Project
  start_year: "2022"
"""
        )
        resume_data = load_resume_data(data_dir)
        assert len(resume_data.projects) == 1
        assert resume_data.projects[0].name == "Side Project"
