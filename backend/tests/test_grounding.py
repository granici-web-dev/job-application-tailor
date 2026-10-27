from backend.grounding import (
    missing_required_skills,
    skill_group_findings,
    skill_wording,
    unsupported_skills,
    with_master_skill_groups,
)

MASTER = """# Serghei Granici

## Kenntnisse und Fähigkeiten

- HTML
- CSS / SASS / SCSS / Tailwind
- JavaScript / TypeScript
- React
- Node.js / Express
- MySQL / MongoDB
- Docker / AWS / Linux
- Git / GitHub
- WebSockets
- Figma / Figma MCP
- Agile / Kanban

## Berufserfahrung

### Senior UI/UX Designer — dilotec GmbH, Köln

- Entwicklung und Pflege von Designsystemen und Komponentenbibliotheken
- Erstellung von UI-Komponenten mit State Management

## Ausbildung

- Tech-Stack: REST API, JWT, Redux
"""


def _cv(skills_block: str) -> str:
    return f"# Serghei Granici\n\n## Profil\n\nText.\n\n## Kenntnisse\n\n{skills_block}\n\n## Sprachen\n\n- Deutsch\n"


def test_flags_skill_imported_from_the_job_posting():
    cv = _cv("**Methoden:** Agile / Kanban, Code-Review, Frontend-Architektur")
    assert unsupported_skills(cv, MASTER) == ["Code-Review", "Frontend-Architektur"]


def test_accepts_skills_the_master_cv_states():
    cv = _cv("**Frontend:** React, TypeScript, HTML, CSS / SASS / Tailwind\n\n**Tools:** Git / GitHub, Docker")
    assert unsupported_skills(cv, MASTER) == []


def test_accepts_plural_and_hyphen_variants_of_master_wording():
    cv = _cv("**Backend:** REST-APIs, WebSockets\n\n**Design:** Design-Systeme, UI-Komponenten")
    assert unsupported_skills(cv, MASTER) == []


def test_splits_parenthesised_examples_into_their_own_items():
    cv = _cv("**Methoden:** Agile / Kanban · Werkzeuge (Docker, Kubernetes)")
    assert unsupported_skills(cv, MASTER) == ["Werkzeuge", "Kubernetes"]


def test_ignores_a_bold_category_label_without_a_colon():
    cv = _cv("- **Design & Prototyping** (Figma, React)")
    assert unsupported_skills(cv, MASTER) == []


def test_reads_only_the_skills_section():
    cv = (
        "# Serghei Granici\n\n## Profil\n\nErfahrung mit Kubernetes und Terraform.\n\n"
        "## Kenntnisse\n\n- React\n\n## Berufserfahrung\n\n- Einsatz von Kubernetes\n"
    )
    assert unsupported_skills(cv, MASTER) == []


def test_returns_nothing_when_the_cv_has_no_skills_section():
    cv = "# Serghei Granici\n\n## Profil\n\nText.\n\n## Sprachen\n\n- Deutsch\n"
    assert unsupported_skills(cv, MASTER) == []


def test_reports_each_unsupported_skill_once():
    cv = _cv("**A:** Kubernetes, React\n\n**B:** Kubernetes")
    assert unsupported_skills(cv, MASTER) == ["Kubernetes"]


def test_recognizes_an_english_skills_heading():
    cv = "# Name\n\n## Skills\n\n- Kubernetes\n\n## Languages\n\n- German\n"
    assert unsupported_skills(cv, MASTER) == ["Kubernetes"]


def test_flags_a_required_skill_the_cv_dropped():
    cv = _cv("**Frontend:** React, HTML")

    assert missing_required_skills(cv, MASTER, ["React", "Docker", "TypeScript"]) == [
        "Docker",
        "TypeScript",
    ]


def test_ignores_a_required_skill_the_master_cv_does_not_back():
    cv = _cv("**Frontend:** React")

    assert missing_required_skills(cv, MASTER, ["Kubernetes", "Rust"]) == []


def test_counts_a_skill_as_present_anywhere_in_the_cv():
    cv = _cv("**Frontend:** React")

    assert missing_required_skills(cv, MASTER, ["Profil"]) == []


def test_matches_a_required_skill_through_the_master_cv_wording_variant():
    cv = _cv("**Backend:** REST-APIs, WebSockets")

    assert missing_required_skills(cv, MASTER, ["REST API", "WebSocket"]) == []


def test_reports_each_missing_skill_once():
    cv = _cv("**Frontend:** React")

    assert missing_required_skills(cv, MASTER, ["Docker", "Docker"]) == ["Docker"]


def test_splits_a_group_laid_out_with_pipes():
    cv = _cv("**Design:** Figma / Figma MCP | UI-Komponenten | Design-Systeme")

    assert unsupported_skills(cv, MASTER) == []


def test_splits_a_group_laid_out_with_bullets():
    cv = _cv("**Frontend:** React • TypeScript • HTML")

    assert unsupported_skills(cv, MASTER) == []


def test_skill_wording_keeps_labels_and_parentheses_whole():
    master = (
        "## Kenntnisse und Fähigkeiten\n\n"
        "- **Frontend:** HTML, React\n"
        "- **Qualität:** UX/UI-Audits, Accessibility (WCAG 2.2 AA)\n\n"
        "## Berufserfahrung\n\n- Redesign\n"
    )

    assert skill_wording(master) == [
        "Frontend: HTML, React",
        "Qualität: UX/UI-Audits, Accessibility (WCAG 2.2 AA)",
    ]


GROUPED_MASTER = """# Serghei Granici

## Kenntnisse und Fähigkeiten

- **Frontend:** HTML, React, TypeScript
- **AI & Tools:** Claude Code, Figma
- **AI-Entwicklung:** LLM-Integration (Anthropic API, Tool Use), Prozessautomatisierung
- **Methoden:** Agile, Kanban

## Berufserfahrung

- Arbeit
"""


def _grouped_cv(skills):
    return f"# Serghei Granici\n\n## Berufserfahrung\n\n- Arbeit\n\n## Kenntnisse\n\n{skills}\n\n---\n\n## Sprachen\n\n- Deutsch\n"


def test_groups_reordered_thinned_and_left_out_pass():
    cv = _grouped_cv("**AI-Entwicklung:** Prozessautomatisierung, LLM-Integration\n\n**Frontend:** React, HTML")

    assert skill_group_findings(cv, GROUPED_MASTER) == []


def test_a_renamed_group_is_caught():
    cv = _grouped_cv("**AI-gestützte Entwicklung:** LLM-Integration, Prozessautomatisierung")

    findings = skill_group_findings(cv, GROUPED_MASTER)

    assert len(findings) == 1
    assert findings[0].startswith("The skill group 'AI-gestützte Entwicklung' is not one of the master CV's.")


def test_a_skill_moved_into_another_group_is_caught_as_a_merge():
    cv = _grouped_cv("**AI-Entwicklung:** LLM-Integration, Claude Code")

    assert skill_group_findings(cv, GROUPED_MASTER) == [
        "'Claude Code' is under the skill group 'AI-Entwicklung', but the master CV lists it under 'AI & Tools'."
    ]


def test_a_skills_line_without_a_label_and_a_doubled_group_are_caught():
    cv = _grouped_cv("React, HTML\n\n**Frontend:** React\n\n**Frontend:** HTML")

    findings = skill_group_findings(cv, GROUPED_MASTER)

    assert findings[0].startswith("The skills line 'React, HTML' has no group label.")
    assert findings[1] == "The skill group 'Frontend' appears twice."


def test_the_fallback_puts_back_the_master_groups_as_they_stand():
    cv = _grouped_cv("**AI-gestützte Entwicklung:** LLM-Integration, Claude Code")

    fixed = with_master_skill_groups(cv, GROUPED_MASTER)

    assert fixed == (
        "# Serghei Granici\n\n## Berufserfahrung\n\n- Arbeit\n\n## Kenntnisse\n\n"
        "- **Frontend:** HTML, React, TypeScript\n"
        "- **AI & Tools:** Claude Code, Figma\n"
        "- **AI-Entwicklung:** LLM-Integration (Anthropic API, Tool Use), Prozessautomatisierung\n"
        "- **Methoden:** Agile, Kanban\n\n---\n\n## Sprachen\n\n- Deutsch\n"
    )
    assert skill_group_findings(fixed, GROUPED_MASTER) == []
