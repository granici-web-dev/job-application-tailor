from backend.tailor_cv import move_skills_after_experience

CV = """# Serghei Granici

**Product Designer**

## Profil

Text.

---

## Kenntnisse

**Design & UX**
Figma, UI/UX Design

---

## Berufserfahrung

### Senior UI/UX Designer — dilotec GmbH

- Ein Punkt

---

## Ausbildung

### Weiterbildung

---

## Sprachen

- Deutsch
"""


def _headings(markdown: str) -> list[str]:
    return [line for line in markdown.splitlines() if line.startswith("## ")]


def test_skills_move_below_experience():
    result = move_skills_after_experience(CV)

    assert _headings(result) == [
        "## Profil",
        "## Berufserfahrung",
        "## Kenntnisse",
        "## Ausbildung",
        "## Sprachen",
    ]


def test_moving_the_section_keeps_its_content_and_the_rest_of_the_cv():
    result = move_skills_after_experience(CV)

    assert "**Design & UX**\nFigma, UI/UX Design" in result
    assert result.startswith("# Serghei Granici\n\n**Product Designer**")
    assert sorted(result.splitlines()) == sorted(CV.splitlines())


def test_a_cv_already_in_order_is_left_alone():
    already = move_skills_after_experience(CV)

    assert move_skills_after_experience(already) == already


def test_english_headings_are_recognized():
    english = CV.replace("## Kenntnisse", "## Skills").replace(
        "## Berufserfahrung", "## Experience"
    )

    assert _headings(move_skills_after_experience(english))[:3] == [
        "## Profil",
        "## Experience",
        "## Skills",
    ]


def test_a_cv_without_one_of_the_two_sections_is_left_alone():
    without_skills = CV.replace("## Kenntnisse", "## Zertifikate")

    assert move_skills_after_experience(without_skills) == without_skills


def test_the_trailing_newline_is_preserved_either_way():
    assert move_skills_after_experience(CV).endswith("- Deutsch\n")
    assert not move_skills_after_experience(CV.rstrip("\n")).endswith("\n")
