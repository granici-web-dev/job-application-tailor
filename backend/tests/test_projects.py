from backend.tailor_cv import with_relevant_projects

MASTER = """# Serghei Granici

## Berufserfahrung

### Senior UI/UX Designer — dilotec GmbH, Köln

- Designsysteme

## Projekte

### Website für eine Arztpraxis (Moldau)

_2026 – heute_

_Tags: engineering, design_

- Website in drei Sprachen

### CRM-Digest-Bot für ein Möbelunternehmen (Rumänien)

_09/2026 – heute_

_Tags: engineering, ai, analysis_

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


def test_the_tag_lines_never_reach_the_cv():
    for discipline in ("ai", "design", "engineering", "unknown", None):
        assert "_Tags:" not in with_relevant_projects(MASTER, discipline)


def test_the_entry_keeps_its_layout_without_the_tag_line():
    master = with_relevant_projects(MASTER, "ai")

    assert (
        "### CRM-Digest-Bot für ein Möbelunternehmen (Rumänien)\n\n_09/2026 – heute_\n\n"
        "- Berichte aus dem CRM\n\n## Ausbildung"
    ) in master


def test_every_project_stays_when_none_is_tagged_for_the_discipline():
    for discipline in ("unknown", None):
        master = with_relevant_projects(MASTER, discipline)

        assert "Arztpraxis" in master and "CRM-Digest-Bot" in master


def test_the_rest_of_the_master_cv_is_untouched():
    master = with_relevant_projects(MASTER, "ai")

    assert master.startswith(MASTER[: MASTER.index("## Projekte")])
    assert master.endswith("## Ausbildung\n\n### Weiterbildung\n")


def test_a_master_cv_without_projects_comes_back_unchanged():
    master = "# Name\n\n## Berufserfahrung\n\n- Arbeit\n"

    assert with_relevant_projects(master, "ai") == master
