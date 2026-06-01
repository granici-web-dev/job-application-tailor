import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.analyze import _strip_json_fences, analyze_job
from backend.errors import JobAnalysisError
from backend.models import JobAnalysis

VALID_ANALYSIS = {
    "company_name": "Acme GmbH",
    "employee_count": None,
    "job_title": "Senior Backend Engineer",
    "employment_type": "remote",
    "location": "Berlin",
    "hard_skills": ["Python", "FastAPI"],
    "soft_skills": ["Collaboration"],
    "keywords": ["Python", "REST", "PostgreSQL"],
    "key_responsibilities": ["Build backend services"],
    "language_requirements": ["English"],
}


def _message(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _client_returning(*texts):
    client = Mock()
    client.messages.create.side_effect = [_message(text) for text in texts]
    return client


def test_analyze_strips_json_fences_and_parses():
    client = _client_returning("```json\n" + json.dumps(VALID_ANALYSIS) + "\n```")

    analysis = analyze_job("job text", client=client, model="claude-sonnet-4-6")

    assert isinstance(analysis, JobAnalysis)
    assert analysis.company_name == "Acme GmbH"
    assert analysis.employment_type == "remote"
    assert analysis.hard_skills == ["Python", "FastAPI"]


def test_analyze_retries_once_on_invalid_json():
    client = _client_returning("not json at all", json.dumps(VALID_ANALYSIS))

    analysis = analyze_job("job text", client=client, model="claude-sonnet-4-6")

    assert analysis.job_title == "Senior Backend Engineer"
    assert client.messages.create.call_count == 2


def test_analyze_raises_after_two_invalid_responses():
    client = _client_returning("nope", "still nope")

    with pytest.raises(JobAnalysisError, match="valid JSON"):
        analyze_job("job text", client=client, model="claude-sonnet-4-6")

    assert client.messages.create.call_count == 2


def test_strip_json_fences_passes_through_plain_json():
    assert _strip_json_fences('{"a": 1}') == '{"a": 1}'
