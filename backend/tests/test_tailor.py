from types import SimpleNamespace
from unittest.mock import Mock

from backend.models import JobAnalysis
from backend.profile import PersonalInfo, Profile
from backend.tailor_cv import build_cv_prompt, tailor_cv
from backend.tailor_letter import build_letter_prompt, tailor_letter

ANALYSIS = JobAnalysis.from_response_dict(
    {
        "company_name": "Acme GmbH",
        "job_title": "Senior Backend Engineer",
        "employment_type": "remote",
        "hard_skills": ["Python", "Kubernetes", "Rust"],
        "keywords": ["Python", "Rust", "microservices"],
        "key_responsibilities": ["Build backend services"],
    }
)

PROFILE = Profile(
    personal=PersonalInfo(
        full_name="Ivan Petrov",
        email="ivan@example.com",
        phone="+49 151 23456789",
        location="Siegburg, Germany",
        linkedin="https://linkedin.com/in/ivanpetrov",
        github=None,
        languages=["German (B2)", "English (C1)"],
    ),
    master_cv_markdown="## Skills\nPython, FastAPI, PostgreSQL, Docker",
    cover_letter_template="Dear team,\n\nKind regards,\nIvan",
)


def _client_returning(text):
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)]
    )
    return client


def test_tailor_cv_returns_markdown_from_model():
    client = _client_returning("# Ivan Petrov\n\n## Summary\nBackend engineer.")

    result = tailor_cv(ANALYSIS, PROFILE, client=client, model="claude-sonnet-4-6")

    assert result.startswith("# Ivan Petrov")
    assert client.messages.create.call_count == 1


def test_cv_prompt_carries_no_fabrication_rule_and_profile_content():
    system_prompt, user_message = build_cv_prompt(ANALYSIS, PROFILE)

    assert "never add a skill" in system_prompt.lower()
    assert "+49 151 23456789" in user_message
    assert "Siegburg, Germany" in user_message
    assert "German (B2)" in user_message
    assert "Python, FastAPI, PostgreSQL, Docker" in user_message


def test_cv_prompt_uses_explicit_language_when_given():
    _, user_message = build_cv_prompt(ANALYSIS, PROFILE, language="German")

    assert "Write the CV in German." in user_message


def test_cv_prompt_requires_posting_language_headings():
    system_prompt, _ = build_cv_prompt(ANALYSIS, PROFILE)

    assert "language of the job posting" in system_prompt
    assert "Berufserfahrung" in system_prompt


def test_cv_prompt_forbids_invented_soft_skills():
    system_prompt, _ = build_cv_prompt(ANALYSIS, PROFILE)

    assert "soft skills" in system_prompt.lower()
    assert "kommunikationsstark" in system_prompt


def test_letter_prompt_carries_no_fabrication_rule_and_template():
    system_prompt, user_message = build_letter_prompt(ANALYSIS, PROFILE)

    assert "never add a skill" in system_prompt.lower()
    assert "Dear team," in user_message
    assert "Acme GmbH" in user_message


def test_tailor_letter_returns_markdown_from_model():
    client = _client_returning("Dear Acme GmbH team,\n\nKind regards,\nIvan")

    result = tailor_letter(ANALYSIS, PROFILE, client=client, model="claude-sonnet-4-6")

    assert "Acme GmbH" in result
    assert client.messages.create.call_count == 1
