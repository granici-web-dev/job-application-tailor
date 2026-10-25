from backend.page_limit import collapse_early_roles, trim_older_roles
from backend.render_pdf import CV_CSS, render_markdown_with_page_count

CV = """# Serghei Granici

## Berufserfahrung

### Senior UI/UX Designer — dilotec GmbH, Köln

_03/2020 – 07/2025_

- Aufbau von Designsystemen
- Usability-Reviews
- Design-Spezifikationen

### UI/UX Designer — Shirtee GmbH, Köln

_05/2019 – 03/2020_

- Shopify-Shops für Creator
- Responsive Layouts
- Landingpages

### Webdesigner — StarSoft SRL, Chisinau

_06/2014 – 04/2016_

- UI/UX für Web-Anwendungen
- Branding und Design-Guidelines

### Grafikdesigner — NEFELE SRL, Chisinau

_09/2013 – 06/2014_

- Designkonzepte und Printmedien

## Ausbildung

### Bachelor of Arts — Slawische Universität, Chisinau, Moldau

_09/2009 – 09/2013_

- Abschluss
- Zweiter Punkt
- Dritter Punkt
"""


def test_roles_started_before_2015_collapse_to_one_line_each():
    collapsed, names = collapse_early_roles(CV)

    assert names == ["Webdesigner — StarSoft SRL, Chisinau", "Grafikdesigner — NEFELE SRL, Chisinau"]
    assert "### Webdesigner — StarSoft SRL, Chisinau (06/2014 – 04/2016)" in collapsed
    assert "### Grafikdesigner — NEFELE SRL, Chisinau (09/2013 – 06/2014)" in collapsed
    assert "UI/UX für Web-Anwendungen" not in collapsed
    assert "Designkonzepte und Printmedien" not in collapsed


def test_collapsing_leaves_later_roles_and_other_sections_alone():
    collapsed, _ = collapse_early_roles(CV)

    assert "- Shopify-Shops für Creator\n- Responsive Layouts\n- Landingpages" in collapsed
    # Education is older than 2015 too, but it is not a role.
    assert "_09/2009 – 09/2013_\n\n- Abschluss\n- Zweiter Punkt\n- Dritter Punkt" in collapsed
    assert collapsed.endswith("- Dritter Punkt\n")


def test_collapsing_twice_changes_nothing_the_second_time():
    collapsed, _ = collapse_early_roles(CV)

    assert collapse_early_roles(collapsed) == (collapsed, [])


def test_roles_started_before_2020_keep_their_first_two_bullets():
    trimmed, names = trim_older_roles(collapse_early_roles(CV)[0])

    assert names == ["UI/UX Designer — Shirtee GmbH, Köln"]
    assert "_05/2019 – 03/2020_\n\n- Shopify-Shops für Creator\n- Responsive Layouts\n" in trimmed
    assert "Landingpages" not in trimmed
    # dilotec started in 2020 and keeps all three.
    assert "- Design-Spezifikationen" in trimmed
    assert "- Dritter Punkt" in trimmed


def test_a_role_already_within_two_bullets_is_not_reported_as_trimmed():
    within = CV.replace("- Landingpages\n", "")

    assert trim_older_roles(within) == (within, [])


def test_the_page_count_comes_from_the_rendered_pdf():
    long_cv = "# Name\n\n## Berufserfahrung\n\n" + "\n".join(f"- Punkt {n}" for n in range(200))

    pdf, pages = render_markdown_with_page_count(long_cv, css=CV_CSS, line_breaks=True)

    assert pdf.startswith(b"%PDF")
    assert pages > 2
    assert render_markdown_with_page_count("# Name", css=CV_CSS)[1] == 1
