from backend.tailor_cv import put_back_master_summary, split_off_summary

MASTER = """# Serghei Granici

## Persönliche Daten

- **E-Mail:** granici.design@gmail.com

## Profil

Frontend Developer mit über 10 Jahren Erfahrung im UI/UX-Design. Verantworte Projekte eigenständig.

## Kenntnisse

- React
"""

CV = """# Serghei Granici

**Frontend Developer**

granici.design@gmail.com

---

## Profil

Projekte werden eigenständig bis zum Deployment umgesetzt.

---

## Berufserfahrung

- Bullet
"""


def test_the_summary_is_split_off_with_its_separator():
    rest, removed = split_off_summary(CV)

    assert "## Profil" not in rest
    assert "Deployment" not in rest
    assert rest.endswith("---\n\n## Berufserfahrung\n\n- Bullet\n")
    assert removed[0] == "## Profil"


def test_the_master_paragraph_goes_back_in_word_for_word_where_the_summary_was():
    rest, removed = split_off_summary(CV)

    result = put_back_master_summary(rest, removed, MASTER)

    assert result == CV.replace(
        "Projekte werden eigenständig bis zum Deployment umgesetzt.",
        "Frontend Developer mit über 10 Jahren Erfahrung im UI/UX-Design. Verantworte Projekte eigenständig.",
    )


def test_the_tailored_heading_is_kept_so_the_section_matches_the_cv_language():
    english = CV.replace("## Profil", "## Summary")

    result = put_back_master_summary(*split_off_summary(english), MASTER)

    assert "## Summary\n\nFrontend Developer mit über 10 Jahren" in result


def test_a_cv_without_a_summary_gets_the_master_section_before_its_first_section():
    without = CV.replace("## Profil\n\nProjekte werden eigenständig bis zum Deployment umgesetzt.\n\n---\n\n", "")
    rest, removed = split_off_summary(without)

    result = put_back_master_summary(rest, removed, MASTER)

    assert removed is None
    assert "---\n\n## Profil\n\nFrontend Developer mit über 10 Jahren" in result
    assert result.index("## Profil") < result.index("## Berufserfahrung")


def test_a_master_cv_without_a_summary_leaves_the_cv_without_one():
    rest, removed = split_off_summary(CV)

    assert put_back_master_summary(rest, removed, MASTER.replace("## Profil", "## Über mich")) == rest
