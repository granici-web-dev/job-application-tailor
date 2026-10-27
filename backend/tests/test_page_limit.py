from backend.page_limit import (
    collapse_early_roles,
    drop_irrelevant_skill_group,
    drop_second_project,
    fit_to_page_limit,
    trim_older_roles,
)
from backend.render_pdf import (
    CV_CSS,
    DEFAULT_CV_LAYOUT,
    CvLayout,
    cv_css,
    render_markdown_with_page_count,
)

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


def _render_needing(*, compact=False, margin=None, font=None, content_cut=False):
    """A fake renderer: 3 pages until every named condition holds, then 2."""

    def render(markdown, layout):
        fits = (
            (not content_cut or "Landingpages" not in markdown)
            and (not compact or layout.compact_spacing)
            and (margin is None or layout.margin_vertical_mm <= margin)
            and (font is None or layout.font_pt <= font)
        )
        render.calls.append(layout)
        return b"%PDF", 2 if fits else 3

    render.calls = []
    return render


def test_a_cv_that_fits_is_rendered_once_with_the_default_layout():
    render = _render_needing()

    fitted = fit_to_page_limit(CV, render)

    assert (fitted.pages, fitted.layout, fitted.markdown) == (2, DEFAULT_CV_LAYOUT, CV)
    assert len(render.calls) == 1


def test_the_layout_tightens_only_after_the_content_steps():
    render = _render_needing(compact=True)

    fitted = fit_to_page_limit(CV, render)

    assert fitted.pages == 2
    assert fitted.layout == CvLayout(compact_spacing=True)
    assert "Landingpages" not in fitted.markdown  # both content steps ran first
    assert render.calls[-1] == CvLayout(compact_spacing=True)


def test_margins_go_to_15_mm_only_when_tighter_spacing_was_not_enough():
    fitted = fit_to_page_limit(CV, _render_needing(compact=True, margin=15))

    assert fitted.layout == CvLayout(compact_spacing=True, margin_vertical_mm=15, margin_horizontal_mm=15)


def test_the_font_never_goes_below_10_pt_and_the_cv_goes_out_anyway():
    render = _render_needing(font=9)

    fitted = fit_to_page_limit(CV, render)

    assert fitted.pages == 3
    assert fitted.layout.font_pt == 10
    assert fitted.layout.margin_vertical_mm == 15
    assert fitted.pdf == b"%PDF"


def test_layout_overrides_are_appended_to_the_base_css():
    css = cv_css(CvLayout(compact_spacing=True, margin_vertical_mm=15, margin_horizontal_mm=15, font_pt=9.5))

    assert css.startswith(CV_CSS)
    assert "h2 { margin: 8pt 0 3pt; }" in css
    assert css.rstrip().endswith("@page { margin: 15mm 15mm; }\nbody { font-size: 9.5pt; }")
    assert cv_css() == CV_CSS


def test_tighter_spacing_and_margins_really_shorten_the_rendered_cv():
    long_cv = "# Name\n\n" + "\n\n".join(
        f"## Abschnitt {n}\n\n### Eintrag\n\n" + "\n".join(f"- Punkt {m}" for m in range(6)) for n in range(10)
    )

    _, normal = render_markdown_with_page_count(long_cv, css=cv_css(), line_breaks=True)
    _, tight = render_markdown_with_page_count(
        long_cv,
        css=cv_css(CvLayout(compact_spacing=True, margin_vertical_mm=15, margin_horizontal_mm=15)),
        line_breaks=True,
    )

    # Ten such sections run onto a third page as set by default and fit two when tightened.
    assert (normal, tight) == (3, 2)


SKILLS_CV = """# Serghei Granici

## Berufserfahrung

### Frontend Developer — CorLab

_05/2026 – heute_

- Arbeit

## Kenntnisse

**Frontend:** HTML, React, TypeScript

**Backend & Daten:** Node.js, REST API, PostgreSQL

**UI/UX Design:** Wireframing, Prototyping

**AI & Tools:** Claude Code, Figma

**Qualität:** Accessibility (WCAG 2.2 AA)

**Methoden:** Agile, Kanban

## Sprachen

- Deutsch
"""
TERMS = ["react", "REST APIs", "WCAG"]


def _labels(cv):
    return [line.split(":**")[0].strip("*") for line in cv.splitlines() if line.startswith("**")]


def test_the_last_group_naming_no_posting_term_goes_first():
    shorter, dropped = drop_irrelevant_skill_group(SKILLS_CV, TERMS)

    assert dropped == ["Methoden"]
    assert _labels(shorter) == ["Frontend", "Backend & Daten", "UI/UX Design", "AI & Tools", "Qualität"]
    assert "**Qualität:** Accessibility (WCAG 2.2 AA)\n\n## Sprachen" in shorter


def test_matching_ignores_case_and_runs_both_ways():
    """'react' finds React; the group's 'REST API' answers the posting's 'REST APIs'."""
    backend_last = SKILLS_CV.replace("**Backend & Daten:** Node.js, REST API, PostgreSQL\n\n", "").replace(
        "**Methoden:** Agile, Kanban", "**Methoden:** Agile, Kanban\n\n**Backend & Daten:** Node.js, REST API, PostgreSQL"
    )

    _, dropped = drop_irrelevant_skill_group(backend_last, ["REST APIs"])
    _, dropped_by_case = drop_irrelevant_skill_group(backend_last.replace("REST API", "Python"), ["python"])

    assert dropped == ["Methoden"]
    assert dropped_by_case == ["Methoden"]


def test_four_groups_always_stay():
    cv, dropped = SKILLS_CV, ["start"]
    while dropped:
        cv, dropped = drop_irrelevant_skill_group(cv, [])

    assert len(_labels(cv)) == 4


def test_skill_groups_go_after_the_role_steps_and_before_the_layout():
    def render(markdown, layout):
        render.calls.append(layout)
        return b"%PDF", 2 if len(_labels(markdown)) <= 4 else 3

    render.calls = []

    fitted = fit_to_page_limit(SKILLS_CV, render, TERMS)

    assert fitted.pages == 2
    assert _labels(fitted.markdown) == ["Frontend", "Backend & Daten", "UI/UX Design", "Qualität"]
    assert fitted.layout == DEFAULT_CV_LAYOUT  # the layout was never touched


def test_without_posting_terms_the_groups_still_go_down_to_four_before_the_layout():
    render = _render_needing(compact=True)

    fitted = fit_to_page_limit(SKILLS_CV, render)

    assert len(_labels(fitted.markdown)) == 4
    assert fitted.layout == CvLayout(compact_spacing=True)


PROJECTS_CV = """# Serghei Granici

## Projekte

### Website für eine Arztpraxis (Moldau)

_2026 – heute_

- Website in drei Sprachen

### CRM-Digest-Bot für ein Möbelunternehmen (Rumänien)

_09/2026 – heute_

- Berichte aus dem CRM

**Tech-Stack:** Python

---

## Kenntnisse

**Frontend:** React
"""


def test_the_second_project_goes_and_the_first_stays():
    shorter, dropped = drop_second_project(PROJECTS_CV)

    assert dropped == ["CRM-Digest-Bot für ein Möbelunternehmen (Rumänien)"]
    assert shorter == (
        "# Serghei Granici\n\n## Projekte\n\n### Website für eine Arztpraxis (Moldau)\n\n"
        "_2026 – heute_\n\n- Website in drei Sprachen\n\n---\n\n## Kenntnisse\n\n**Frontend:** React\n"
    )


def test_a_single_project_is_never_dropped():
    shorter, _ = drop_second_project(PROJECTS_CV)

    assert drop_second_project(shorter) == (shorter, [])


def test_the_second_project_goes_after_the_skill_groups_and_before_the_layout():
    def render(markdown, layout):
        render.calls.append(markdown)
        return b"%PDF", 3 if "CRM-Digest-Bot" in markdown else 2

    render.calls = []
    cv = PROJECTS_CV.replace("**Frontend:** React\n", "".join(f"**G{n}:** Agile\n\n" for n in range(6)))

    fitted = fit_to_page_limit(cv, render, ["react"])

    assert fitted.pages == 2
    assert fitted.layout == DEFAULT_CV_LAYOUT
    assert fitted.markdown.count("**G") == 4  # the skill groups went first, down to four
    assert all("CRM-Digest-Bot" in markdown for markdown in render.calls[:-1])


def test_the_second_project_stays_when_the_cv_already_fits():
    fitted = fit_to_page_limit(PROJECTS_CV, lambda markdown, layout: (b"%PDF", 2))

    assert "CRM-Digest-Bot" in fitted.markdown

