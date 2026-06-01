from types import SimpleNamespace
from unittest.mock import Mock

from backend.humanize import (
    build_humanize_prompt,
    extract_factual_tokens,
    facts_preserved,
    humanize,
)

CV_TEXT = """# Ivan Petrov

## Profil
Backend-Entwickler mit 6 Jahren Erfahrung in Python und FastAPI.

## Kenntnisse
Python, FastAPI, PostgreSQL, REST, B2
"""


def _client_returning(text):
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)]
    )
    return client


def test_extract_factual_tokens_captures_numbers_tech_and_contacts():
    tokens = extract_factual_tokens("Kontakt ivan@example.com, 6 Jahre, FastAPI, REST, B2")

    assert "ivan@example.com" in tokens
    assert "6" in tokens
    assert "FastAPI" in tokens
    assert "REST" in tokens
    assert "B2" in tokens
    assert "Kontakt" not in tokens
    assert "Jahre" not in tokens


def test_facts_preserved_true_when_only_prose_rephrased():
    before = "Ich entwickelte Backend-Dienste mit Python und FastAPI über 6 Jahre."
    after = "Über 6 Jahre baute ich mit Python und FastAPI mehrere Backend-Dienste."

    assert facts_preserved(before, after)


def test_facts_preserved_false_when_skill_invented():
    assert not facts_preserved(
        "Erfahrung mit Python und FastAPI.",
        "Erfahrung mit Python, FastAPI und GraphQL.",
    )


def test_facts_preserved_false_when_number_changed():
    assert not facts_preserved("6 Jahre Erfahrung.", "8 Jahre Erfahrung.")


def test_humanize_returns_model_output_when_facts_preserved():
    rephrased = CV_TEXT.replace("mit 6 Jahren Erfahrung in", "seit 6 Jahren mit")
    client = _client_returning(rephrased)

    result = humanize(CV_TEXT, kind="cv", client=client, model="claude-sonnet-4-6")

    assert result == rephrased


def test_humanize_falls_back_to_input_when_facts_changed():
    invented = CV_TEXT.replace("PostgreSQL, REST, B2", "PostgreSQL, REST, B2, GraphQL")
    client = _client_returning(invented)

    result = humanize(CV_TEXT, kind="cv", client=client, model="claude-sonnet-4-6")

    assert result == CV_TEXT


def test_humanize_cv_falls_back_when_a_heading_changes():
    renamed = CV_TEXT.replace("## Kenntnisse", "## Skills")
    client = _client_returning(renamed)

    result = humanize(CV_TEXT, kind="cv", client=client, model="claude-sonnet-4-6")

    assert result == CV_TEXT


def test_build_humanize_prompt_selects_cv_vs_letter_section():
    cv_prompt = build_humanize_prompt("cv")
    letter_prompt = build_humanize_prompt("cover_letter")

    assert "never change the structure" in cv_prompt
    assert "section headings" in cv_prompt
    assert "COVER LETTER" in letter_prompt
