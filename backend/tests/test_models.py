import pytest

from backend.errors import JobAnalysisError
from backend.models import JobAnalysis


def _minimal_response(**overrides):
    data = {"company_name": "Acme GmbH", "job_title": "Backend Engineer"}
    data.update(overrides)
    return data


def test_job_analysis_defaults_unknown_employment_type():
    analysis = JobAnalysis.from_response_dict(_minimal_response(employment_type="freelance-ish"))

    assert analysis.employment_type == "unknown"


def test_job_analysis_preserves_null_employee_count():
    analysis = JobAnalysis.from_response_dict(_minimal_response(employee_count=None))

    assert analysis.employee_count is None


def test_job_analysis_requires_company_name():
    with pytest.raises(JobAnalysisError, match="company_name"):
        JobAnalysis.from_response_dict({"job_title": "Backend Engineer"})


def test_job_analysis_drops_blank_list_entries():
    analysis = JobAnalysis.from_response_dict(
        _minimal_response(hard_skills=["Python", "  ", "", "FastAPI"])
    )

    assert analysis.hard_skills == ["Python", "FastAPI"]


def test_job_analysis_coerces_missing_lists_to_empty():
    analysis = JobAnalysis.from_response_dict(_minimal_response())

    assert analysis.keywords == []
    assert analysis.language_requirements == []
