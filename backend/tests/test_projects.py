from backend.tailor_cv import project_letter_sentence, with_relevant_projects
from backend.tailor_letter import with_project_sentence

MASTER = """# Serghei Granici

## Berufserfahrung

### Senior UI/UX Designer — dilotec GmbH, Köln

- Designsysteme

## Projekte

### Website für eine Arztpraxis (Moldau)

_2026 – heute_

_Tags: engineering, design_

_Letter: Daneben habe ich eine Website gebaut._

- Website in drei Sprachen

### CRM-Digest-Bot für ein Möbelunternehmen (Rumänien)

_09/2026 – heute_

_Tags: engineering, ai, analysis_

_Letter: Daneben habe ich einen Telegram-Bot gebaut._

- Berichte aus dem CRM

## Ausbildung

### Weiterbildung
"""


def test_only_the_projects_tagged_for_the_discipline_stay():
    master = with_relevant_projects(MASTER, "design")

    assert "Arztpraxis" in master
    assert "CRM-Digest-Bot" not in master
    assert master.index("## Projekte") < master.index("Arztpraxis") < master.index("## Ausbildung")


def test_a_discipline_both_projects_carry_keeps_both():
    master = with_relevant_projects(MASTER, "engineering")

    assert "Arztpraxis" in master and "CRM-Digest-Bot" in master


def test_the_tag_and_letter_lines_never_reach_the_cv():
    for discipline in ("ai", "design", "engineering", "unknown", None):
        master = with_relevant_projects(MASTER, discipline)

        assert "_Tags:" not in master
        assert "_Letter:" not in master


def test_the_entry_keeps_its_layout_without_the_tag_line():
    master = with_relevant_projects(MASTER, "ai")

    assert (
        "### CRM-Digest-Bot für ein Möbelunternehmen (Rumänien)\n\n_09/2026 – heute_\n\n"
        "- Berichte aus dem CRM\n\n## Ausbildung"
    ) in master


def test_the_projects_section_goes_when_no_project_is_tagged_for_the_discipline():
    master = with_relevant_projects(MASTER, "unknown")

    assert "## Projekte" not in master
    assert "Arztpraxis" not in master and "CRM-Digest-Bot" not in master
    assert master == MASTER[: MASTER.index("## Projekte")] + "## Ausbildung\n\n### Weiterbildung\n"
    assert project_letter_sentence(MASTER, "unknown") is None


def test_the_letters_master_keeps_every_project_for_the_fact_check():
    master = with_relevant_projects(MASTER, None)

    assert "Arztpraxis" in master and "CRM-Digest-Bot" in master


def test_the_rest_of_the_master_cv_is_untouched():
    master = with_relevant_projects(MASTER, "ai")

    assert master.startswith(MASTER[: MASTER.index("## Projekte")])
    assert master.endswith("## Ausbildung\n\n### Weiterbildung\n")


def test_a_master_cv_without_projects_comes_back_unchanged():
    master = "# Name\n\n## Berufserfahrung\n\n- Arbeit\n"

    assert with_relevant_projects(master, "ai") == master


def test_the_letter_tells_the_first_project_the_cv_keeps():
    assert project_letter_sentence(MASTER, "ai") == "Daneben habe ich einen Telegram-Bot gebaut."
    assert project_letter_sentence(MASTER, "analysis") == "Daneben habe ich einen Telegram-Bot gebaut."
    assert project_letter_sentence(MASTER, "design") == "Daneben habe ich eine Website gebaut."
    # Both projects pass: the first in the master CV's order.
    assert project_letter_sentence(MASTER, "engineering") == "Daneben habe ich eine Website gebaut."


def test_with_no_project_for_the_discipline_the_letter_tells_none():
    for discipline in ("unknown", None):
        assert project_letter_sentence(MASTER, discipline) is None


def test_without_a_project_sentence_the_paragraph_keeps_only_the_weiterbildung():
    template = "Im Juli 2026 habe ich meine Weiterbildung abgeschlossen. [PROJEKT]\n\nIch stehe bereit."

    assert with_project_sentence(template, project_letter_sentence(MASTER, "unknown")) == (
        "Im Juli 2026 habe ich meine Weiterbildung abgeschlossen.\n\nIch stehe bereit."
    )


def test_the_project_sentence_fills_the_template_placeholder():
    template = "Im Juli 2026 habe ich meine Weiterbildung abgeschlossen. [PROJEKT]\n\nIch stehe bereit."

    assert with_project_sentence(template, "Daneben habe ich eine Website gebaut.") == (
        "Im Juli 2026 habe ich meine Weiterbildung abgeschlossen. Daneben habe ich eine Website gebaut."
        "\n\nIch stehe bereit."
    )
    assert with_project_sentence(template, None) == (
        "Im Juli 2026 habe ich meine Weiterbildung abgeschlossen.\n\nIch stehe bereit."
    )

