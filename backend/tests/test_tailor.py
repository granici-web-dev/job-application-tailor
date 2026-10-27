from types import SimpleNamespace
from unittest.mock import Mock

from backend.models import JobAnalysis
from backend.profile import PersonalInfo, Profile
from backend.tailor_cv import build_cv_prompt, tailor_cv
import json

from backend.tailor_letter import build_letter_prompt, parse_letter_template, tailor_letter

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
    cover_letter_template=(
        "[ANREDE]\n\nOpening.\n\nAt DataForge I build APIs.\n\nAvailable now for [UNTERNEHMEN].\n\n"
        "Kind regards,\nIvan"
    ),
)


def _client_returning(text):
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)]
    )
    return client


def test_tailor_cv_returns_markdown_from_model():
    # Carries Python: the one posting skill the master CV backs, so no correction is due.
    client = _client_returning("# Ivan Petrov\n\n## Skills\nPython, FastAPI\n")

    result = tailor_cv(ANALYSIS, PROFILE, client=client, model="claude-sonnet-4-6")

    assert result.startswith("# Ivan Petrov")
    assert client.messages.create.call_count == 1


def test_tailor_cv_asks_again_when_a_required_skill_is_missing():
    client = _client_returning("# Ivan Petrov\n\n## Skills\nFastAPI, Docker\n")

    tailor_cv(ANALYSIS, PROFILE, client=client, model="claude-sonnet-4-6")

    correction = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert client.messages.create.call_count == 2
    assert "left out skills this posting asks for" in correction
    assert "Python" in correction


def test_tailor_cv_does_not_chase_a_posting_skill_the_candidate_lacks():
    client = _client_returning("# Ivan Petrov\n\n## Skills\nPython, FastAPI\n")

    tailor_cv(ANALYSIS, PROFILE, client=client, model="claude-sonnet-4-6")

    # Kubernetes and Rust are on the posting but nowhere in the master CV.
    assert client.messages.create.call_count == 1


def test_tailor_cv_keeps_the_first_cv_when_the_retry_trades_an_omission_for_a_fabrication():
    first = "# Ivan Petrov\n\n## Skills\nFastAPI, Docker\n"
    second = "# Ivan Petrov\n\n## Skills\nPython, FastAPI, Docker, Kubernetes\n"
    client = Mock()
    client.messages.create.side_effect = [
        SimpleNamespace(content=[SimpleNamespace(type="text", text=first)]),
        SimpleNamespace(content=[SimpleNamespace(type="text", text=second)]),
    ]

    result = tailor_cv(ANALYSIS, PROFILE, client=client, model="claude-sonnet-4-6")

    assert result == first


def test_cv_prompt_carries_no_fabrication_rule_and_profile_content():
    system_prompt, user_message = build_cv_prompt(ANALYSIS, PROFILE)

    assert "never add a skill" in system_prompt.lower()
    assert "Never rename, translate, merge or split a group" in system_prompt
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


def test_cv_prompt_forbids_terms_not_in_master_cv():
    system_prompt, _ = build_cv_prompt(ANALYSIS, PROFILE)

    assert "verbatim in the master CV" in system_prompt
    assert "Middleware" in system_prompt


def test_letter_prompt_carries_no_fabrication_rule_and_template():
    system_prompt, user_message = build_letter_prompt(
        ANALYSIS, PROFILE, parse_letter_template(PROFILE.cover_letter_template)
    )

    assert "appear word for word in the master CV" in system_prompt
    assert "## Terms you may use" in user_message
    assert "- Python, FastAPI, PostgreSQL, Docker" in user_message
    assert "At DataForge I build APIs." in user_message
    assert "Available now for Acme GmbH." in user_message
    assert "Acme GmbH" in user_message


def test_tailor_letter_returns_the_assembled_letter_from_one_model_call():
    client = _client_returning(
        json.dumps(
            {
                "salutation": "Dear team,",
                "intro": "Your posting at Acme GmbH caught my eye.",
                "adjusted_paragraph": "At DataForge I build APIs.",
            }
        )
    )

    result = tailor_letter(ANALYSIS, PROFILE, client=client, model="claude-sonnet-4-6")

    assert result == (
        "Dear team,\n\nYour posting at Acme GmbH caught my eye.\n\nAt DataForge I build APIs."
        "\n\nAvailable now for Acme GmbH.\n\nKind regards,\nIvan"
    )
    assert client.messages.create.call_count == 1
