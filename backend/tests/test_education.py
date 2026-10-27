from backend.tailor_cv import (
    education_findings,
    put_back_master_education,
    split_off_education,
)

MASTER = """# Serghei Granici

## Berufserfahrung

### Designer — CorLab

- Arbeit

## Ausbildung

### Weiterbildung zum Fullstack Developer — IT Career Hub, Berlin

_09/2025 – 07/2026 (abgeschlossen)_

- Tech-Stack: HTML, CSS, React.

### Übersiedlung nach Deutschland und Spracherwerb

_2016 – 2019_

- Übersiedlung nach Deutschland 2016, Deutschkurse an der VHS (Zertifikat B1), danach Einzelunterricht bis B2
- Erste Festanstellung in Deutschland 2019

### Bachelor of Arts — Slawische Universität, Chisinau, Moldau

_09/2009 – 09/2013_

## Sprachen

- Deutsch — fließend (B2–C1)
"""
MASTER_EDUCATION = MASTER.split("## Ausbildung\n", 1)[1].split("## Sprachen", 1)[0].strip()


def _cv(education):
    return (
        "# Serghei Granici\n\n---\n\n## Berufserfahrung\n\n### Designer — CorLab\n\n- Arbeit\n\n---\n\n"
        f"{education}"
        "## Sprachen\n\n- Deutsch — fließend (B2–C1)\n"
    )


def _round_trip(cv):
    rest, removed, following = split_off_education(cv)
    return put_back_master_education(rest, removed, following, MASTER)


def test_a_dropped_entry_and_a_thinned_list_come_back_word_for_word():
    shortened = (
        "## Ausbildung\n\n### Weiterbildung zum Fullstack Developer — IT Career Hub, Berlin\n\n"
        "_09/2025 – 07/2026 (abgeschlossen)_\n\n- Tech-Stack: React.\n\n"
        "### Bachelor of Arts — Slawische Universität, Chisinau, Moldau\n\n_09/2009 – 09/2013_\n\n---\n\n"
    )

    rebuilt = _round_trip(_cv(shortened))

    assert rebuilt == _cv(f"## Ausbildung\n\n{MASTER_EDUCATION}\n\n---\n\n")
    assert "### Übersiedlung nach Deutschland und Spracherwerb" in rebuilt
    assert education_findings(rebuilt, MASTER) == []


def test_the_education_never_reaches_what_runs_in_between():
    rest, removed, following = split_off_education(_cv(f"## Ausbildung\n\n{MASTER_EDUCATION}\n\n---\n\n"))

    assert "Ausbildung" not in rest and "Übersiedlung" not in rest
    assert removed[0] == "## Ausbildung"
    assert following == "## Sprachen"


def test_a_cv_without_an_education_section_gets_the_masters_before_the_languages():
    rebuilt = _round_trip(_cv(""))

    assert rebuilt.index("## Ausbildung") < rebuilt.index("## Sprachen")
    assert MASTER_EDUCATION in rebuilt
    assert education_findings(rebuilt, MASTER) == []


def test_an_education_section_off_the_master_is_reported():
    reworded = _cv(f"## Ausbildung\n\n{MASTER_EDUCATION.replace('Erste Festanstellung', 'Erster Job')}\n\n")

    assert education_findings(reworded, MASTER) == [
        "The education section must be the master CV's, word for word: every entry and bullet, in its order."
    ]
    assert education_findings(_cv(""), MASTER) == [
        "The CV has no education section; it carries the master CV's, word for word."
    ]
