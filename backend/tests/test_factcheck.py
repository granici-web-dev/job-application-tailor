from backend.factcheck import check_cv, check_letter, fact_check_correction

MASTER = """# Serghei Granici

## Persönliche Daten

- **Telefon:** +49 1727014108

## Profil

Frontend Developer mit abgeschlossener Weiterbildung zum Fullstack Developer, über 10 Jahren Erfahrung im UI/UX-Design und Fokus auf AI-gestützte Entwicklung.

## Kenntnisse und Fähigkeiten

- **Frontend:** HTML, TypeScript, React, Next.js
- **Backend & Daten:** NestJS, REST API, PostgreSQL, Prisma
- **UI/UX Design:** Designsysteme, Komponentenbibliotheken, Prototyping
- **Qualität:** UX/UI-Audits, Cognitive Walkthrough, Accessibility (WCAG 2.2 AA)
- **AI & Tools:** Claude Code, Figma

## Berufserfahrung

### AI-native Product Designer & Full-stack Developer — CorLab (Praktikum)

_05/2026 – heute_

Eigenverantwortliche Leitung von Projekten, durchgängig mit Claude Code.

**Verwaltungssystem für eine staatliche Stelle (Moldau) – Design und Entwicklung:**

- Prototypen für 6 Rollen auf dem staatlichen Design-System
- Cognitive Walkthrough und WCAG-2.2-AA-Audit vor der Übergabe in die Entwicklung

**Bestehendes Verwaltungssystem (Moldau) – Audit, Redesign und Umsetzung:**

- UX/UI-Audit über 6 Rollen und 3 Sprachen: 48 Befunde
- Redesign auf Basis des Audits

### Senior UI/UX Designer — dilotec GmbH, Köln

_03/2020 – 07/2025_

- Aufbau und Pflege von Designsystemen und Komponentenbibliotheken in Figma

### Webdesigner — StarSoft SRL, Chisinau

_06/2014 – 04/2016_

- UI/UX für Web-Anwendungen

## Projekte

### Website und Back Office für eine Kinderarzt- und Ernährungspraxis (Moldau)

_2026 – heute_

- Öffentliche Website in drei Sprachen mit eigenem CMS

**Tech-Stack:** Next.js 16, React 19, TypeScript, NestJS 11, Prisma 7, PostgreSQL 16

## Ausbildung

### Weiterbildung zum Fullstack Developer — IT Career Hub, Berlin

_09/2025 – 07/2026 (abgeschlossen)_

- Tech-Stack: HTML, TypeScript, React, REST API

## Sprachen

- Deutsch — fließend (B2–C1)
"""

LETTER = """Sehr geehrte Damen und Herren,

mit großem Interesse habe ich Ihre Ausschreibung gelesen.

Aktuell arbeite ich als AI-native Product Designer & Full-stack Developer bei CorLab. Für eine staatliche Stelle entwerfe ich Prototypen für sechs Rollen. Ein zweites, bestehendes System habe ich auditiert und neu gestaltet.

Davor war ich über zehn Jahre im UI/UX-Design tätig, zuletzt bei der dilotec GmbH.

Im Juli 2026 habe ich meine Weiterbildung abgeschlossen. Daneben habe ich eine Plattform für eine Arztpraxis gebaut – mit Next.js, NestJS, Prisma und PostgreSQL.

Mit freundlichen Grüßen
Serghei Granici
"""


def _cv(master=MASTER, **replacements):
    for old, new in replacements.items():
        assert old in master, old
        master = master.replace(old, new)
    return master


def _check_cv(cv, posting_terms=()):
    return check_cv(cv, MASTER, posting_terms=list(posting_terms))


def _check_letter(letter, posting_terms=()):
    return check_letter(letter, MASTER, posting_terms=list(posting_terms))


def test_the_master_cv_passes_its_own_check():
    assert _check_cv(MASTER) == []


def test_a_letter_that_keeps_every_fact_in_place_passes():
    assert _check_letter(LETTER) == []


def test_ten_years_extended_to_wcag_audits_in_the_profile_is_caught():
    cv = _cv(
        **{
            "über 10 Jahren Erfahrung im UI/UX-Design und Fokus auf AI-gestützte Entwicklung.": (
                "Über 10 Jahre UI/UX-Erfahrung in Designsystemen, Komponentenbibliotheken und "
                "WCAG-Audits."
            )
        }
    )

    findings = _check_cv(cv)

    assert any("'WCAG" in finding and "10 years" in finding for finding in findings)
    assert any("'Designsysteme'" in finding and "10 years" in finding for finding in findings)


def test_a_list_after_a_colon_still_counts_as_part_of_the_years_claim():
    cv = _cv(
        **{
            "über 10 Jahren Erfahrung im UI/UX-Design und Fokus auf AI-gestützte Entwicklung.": (
                "über 10 Jahre UI/UX-Erfahrung fließen in die Frontend-Arbeit ein: Figma-Umsetzung, "
                "Designsysteme und WCAG-2.2-AA-konforme Interfaces."
            )
        }
    )

    findings = _check_cv(cv)

    assert any("'Figma'" in finding and "10 years" in finding for finding in findings)
    assert any("'WCAG" in finding and "10 years" in finding for finding in findings)


def test_a_number_the_master_cv_never_states_is_caught():
    findings = _check_cv(_cv(**{"48 Befunde": "47 Befunde"}))

    assert "The number 47 does not appear in the master CV." in findings


def test_a_spelled_out_number_counts_as_that_number():
    assert _check_letter(LETTER.replace("sechs Rollen", "zwanzig Rollen")) == [
        "The number 20 does not appear in the master CV."
    ]


def test_a_number_moved_to_another_position_is_caught():
    cv = _cv(**{"- UI/UX für Web-Anwendungen": "- UI/UX für Web-Anwendungen, 48 Befunde"})

    findings = _check_cv(cv)

    assert len(findings) == 1
    assert "The number 48 is tied to 'Webdesigner — StarSoft SRL, Chisinau'" in findings[0]


def test_a_method_moved_to_another_employer_is_caught():
    cv = _cv(
        **{
            "- Aufbau und Pflege von Designsystemen und Komponentenbibliotheken in Figma": (
                "- Aufbau und Pflege von Designsystemen und WCAG-Audits in Figma"
            )
        }
    )

    findings = _check_cv(cv)

    assert len(findings) == 1
    assert findings[0].startswith("'WCAG' is tied to 'Senior UI/UX Designer — dilotec GmbH, Köln'")
    assert "CorLab" in findings[0]


def test_a_posting_skill_the_master_cv_lacks_is_caught_anywhere():
    cv = _cv(**{"Fokus auf AI-gestützte Entwicklung.": "Fokus auf Barrierefreiheit."})

    assert _check_cv(cv, posting_terms=["Barrierefreiheit", "React"]) == [
        "'Barrierefreiheit' does not appear in the master CV."
    ]


BA_TERMS = ["Business Analyst", "Digitale Plattformen", "Barrierefreiheit", "Services"]
BA_NAMES = ["Business Analyst Digitale Plattformen (m/w/d)", "Kontor Plattform Services GmbH"]


def test_posting_terms_inside_the_job_title_and_company_in_the_letter_pass():
    letter = LETTER.replace(
        "mit großem Interesse habe ich Ihre Ausschreibung gelesen.",
        "mit großem Interesse habe ich Ihre Ausschreibung als Business Analyst Digitale "
        "Plattformen (m/w/d) bei der Kontor Plattform Services GmbH gelesen.",
    )

    assert check_letter(letter, MASTER, posting_terms=BA_TERMS, posting_names=BA_NAMES) == []


def test_a_posting_term_outside_the_job_title_in_the_letter_is_still_caught():
    letter = LETTER.replace(
        "mit großem Interesse habe ich Ihre Ausschreibung gelesen.",
        "mit großem Interesse habe ich Ihre Ausschreibung als Business Analyst Digitale "
        "Plattformen gelesen. Barrierefreiheit liegt mir am Herzen.",
    )

    assert check_letter(letter, MASTER, posting_terms=BA_TERMS, posting_names=BA_NAMES) == [
        "'Barrierefreiheit' does not appear in the master CV."
    ]


def test_a_title_term_used_as_a_claim_outside_the_title_is_still_caught():
    letter = LETTER.replace(
        "Davor war ich über zehn Jahre im UI/UX-Design tätig",
        "Davor war ich als Business Analyst und über zehn Jahre im UI/UX-Design tätig",
    )

    assert check_letter(letter, MASTER, posting_terms=BA_TERMS, posting_names=BA_NAMES) == [
        "'Business Analyst' does not appear in the master CV."
    ]


def test_a_job_title_is_also_recognised_by_its_core_before_the_qualifiers():
    letter = LETTER.replace(
        "mit großem Interesse habe ich Ihre Ausschreibung gelesen.",
        "mit großem Interesse habe ich Ihre Ausschreibung als Software Engineer gelesen.",
    )

    findings = check_letter(
        letter,
        MASTER,
        posting_terms=["Software Engineer", "Barrierefreiheit"],
        posting_names=["Software Engineer (m/w/d) React / TypeScript", "Nordlicht Software GmbH"],
    )

    assert findings == []


def test_an_entry_heading_the_master_cv_does_not_have_is_caught():
    cv = _cv(**{"### Webdesigner — StarSoft SRL, Chisinau": "### Webdesigner — Pixel GmbH, Chisinau"})

    assert _check_cv(cv) == [
        "The entry 'Webdesigner — Pixel GmbH, Chisinau' matches no position or project in the master CV."
    ]


def test_an_employer_entry_that_mentions_the_project_is_caught():
    cv = _cv(
        **{
            "- UX/UI-Audit über 6 Rollen und 3 Sprachen: 48 Befunde": (
                "- UX/UI-Audit über 6 Rollen und 3 Sprachen: 48 Befunde, auch für die Kinderarztpraxis"
            )
        }
    )

    findings = _check_cv(cv)

    assert len(findings) == 1
    assert "mentions 'Website und Back Office" in findings[0]


def test_the_project_told_in_a_paragraph_about_an_employer_is_caught():
    letter = LETTER.replace(
        "entwerfe ich Prototypen für sechs Rollen.",
        "entwerfe ich Prototypen für sechs Rollen. Für eine Kinderarztpraxis habe ich eine "
        "Plattform mit Next.js gebaut.",
    )

    findings = _check_letter(letter)

    assert any("presents the project as work done for that employer" in f for f in findings)


def test_a_sentence_without_a_name_continues_the_position_before_it():
    letter = LETTER.replace(
        "entwerfe ich Prototypen für sechs Rollen.",
        "entwerfe ich Prototypen für sechs Rollen. Dort arbeite ich mit Next.js.",
    )

    findings = _check_letter(letter)

    assert len(findings) == 1
    assert findings[0].startswith("'Next.js' is tied to 'AI-native Product Designer")


def test_a_paragraph_opening_without_a_name_is_held_to_the_whole_master_cv():
    letter = LETTER.replace(
        "mit großem Interesse habe ich Ihre Ausschreibung gelesen.",
        "mit großem Interesse habe ich Ihre Ausschreibung gelesen. Ich arbeite mit React und Figma.",
    )

    assert _check_letter(letter) == []


def test_a_claim_of_years_the_master_cv_never_makes_is_caught():
    findings = _check_letter(LETTER.replace("über zehn Jahre", "über zwölf Jahre"))

    assert any("never claims 12 years" in finding for finding in findings)


def test_compound_spellings_count_as_the_same_skill():
    cv = _cv(
        **{
            "- Aufbau und Pflege von Designsystemen und Komponentenbibliotheken in Figma": (
                "- Aufbau von Design-Systemen und Komponentenbibliotheken mit Figma-Designs"
            )
        }
    )

    assert _check_cv(cv) == []


def test_a_term_inside_a_longer_word_is_not_a_mention():
    cv = _cv(**{"- UI/UX für Web-Anwendungen": "- UI/UX für Web-Anwendungen mit Reactive Forms"})

    assert _check_cv(cv) == []


def test_contact_details_and_the_posting_title_may_carry_their_own_numbers():
    cv = MASTER.replace("# Serghei Granici\n", "# Serghei Granici\n\n**Frontend Developer 3D**\n")
    cv = cv.replace("## Profil", "github.com/granici-42\n\n## Profil")

    findings = check_cv(
        cv, MASTER, posting_terms=[], allowed_text="GitHub: github.com/granici-42\nFrontend Developer 3D"
    )

    assert findings == []


def test_the_correction_lists_every_finding():
    correction = fact_check_correction(["first finding", "second finding"])

    assert correction.startswith("## Fact check")
    assert "- first finding" in correction
    assert "- second finding" in correction


def test_a_method_moved_to_the_other_project_inside_a_position_is_caught_in_the_cv():
    cv = _cv(**{"- Redesign auf Basis des Audits": "- Redesign auf Basis des Audits und WCAG-Audit"})

    findings = _check_cv(cv)

    assert len(findings) == 1
    assert findings[0].startswith(
        "'WCAG' is tied to 'AI-native Product Designer & Full-stack Developer — CorLab (Praktikum) "
        "› Bestehendes Verwaltungssystem (Moldau) – Audit, Redesign und Umsetzung'"
    )
    assert "› Verwaltungssystem für eine staatliche Stelle" in findings[0]


def test_a_method_moved_to_the_other_project_inside_a_position_is_caught_in_the_letter():
    letter = LETTER.replace(
        "Ein zweites, bestehendes System habe ich auditiert und neu gestaltet.",
        "Ein zweites, bestehendes System habe ich mit einem WCAG-Audit geprüft.",
    )

    findings = _check_letter(letter)

    assert len(findings) == 1
    assert "'WCAG' is tied to" in findings[0]
    assert "› Bestehendes Verwaltungssystem" in findings[0]


def test_a_line_that_names_a_project_outranks_the_subheading_above_it():
    cv = _cv(
        **{
            "- Redesign auf Basis des Audits": (
                "- Redesign auf Basis des Audits\n"
                "- Für die staatliche Stelle: Cognitive Walkthrough vor der Übergabe"
            )
        }
    )

    assert _check_cv(cv) == []


def test_a_sentence_about_the_position_as_a_whole_may_draw_on_all_its_projects():
    letter = LETTER.replace(
        "Aktuell arbeite ich als AI-native Product Designer & Full-stack Developer bei CorLab.",
        "Aktuell arbeite ich bei CorLab an Prototypen, WCAG-Audits und UX/UI-Audits.",
    )

    assert _check_letter(letter) == []
