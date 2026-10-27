from backend.tailor_cv import with_master_bullets

MASTER = """# Serghei Granici

## Berufserfahrung

### Product Designer — CorLab (Praktikum)

_05/2026 – heute_

Eigenverantwortliche Leitung von Projekten.

**Verwaltungssystem:**

- Stakeholder-Analyse
- 112 Use Cases
- Umsetzung als Fullstack-Anwendung

**Bestehendes System:**

- UX/UI-Audit über 6 Rollen
- Redesign auf Basis des Audits

### Webdesigner — StarSoft SRL, Chisinau

_06/2014 – 04/2016_

- UI/UX für Web-Anwendungen
- Branding, Farb- und Typografie-Systeme

## Projekte

### CRM-Digest-Bot

_09/2026 – heute_

- Automatisierte Berichte
- Chat mit Claude
- 6 Datenquellen

**Tech-Stack:** Python

## Ausbildung

### Weiterbildung

_2025_

- Tech-Stack: React
"""


def test_a_missing_bullet_comes_back_after_the_one_it_follows_in_the_master():
    cv = MASTER.replace("- 112 Use Cases\n", "").replace("- Branding, Farb- und Typografie-Systeme\n", "")

    assert with_master_bullets(cv, MASTER) == MASTER


def test_an_extra_bullet_goes():
    cv = MASTER.replace("- Chat mit Claude\n", "- Chat mit Claude\n- Ein erfundener Punkt\n")

    assert with_master_bullets(cv, MASTER) == MASTER


def test_a_reworded_bullet_is_replaced_by_the_master_wording():
    cv = MASTER.replace("- Umsetzung als Fullstack-Anwendung\n", "- Fullstack-Anwendung komplett selbst umgesetzt\n")

    assert with_master_bullets(cv, MASTER) == MASTER


def test_the_order_within_an_entry_stays_the_models():
    reordered = MASTER.replace(
        "- Stakeholder-Analyse\n- 112 Use Cases\n- Umsetzung als Fullstack-Anwendung\n",
        "- Umsetzung als Fullstack-Anwendung\n- Stakeholder-Analyse\n",
    )

    rebuilt = with_master_bullets(reordered, MASTER)

    assert "- Umsetzung als Fullstack-Anwendung\n- Stakeholder-Analyse\n- 112 Use Cases\n" in rebuilt


def test_a_whole_list_left_out_comes_back_under_its_subheading():
    cv = MASTER.replace("**Bestehendes System:**\n\n- UX/UI-Audit über 6 Rollen\n- Redesign auf Basis des Audits\n\n", "")

    assert with_master_bullets(cv, MASTER) == MASTER


def test_education_bullets_are_not_touched():
    cv = MASTER.replace("- Tech-Stack: React", "- Tech-Stack: React, Vue")

    assert "- Tech-Stack: React, Vue" in with_master_bullets(cv, MASTER)
