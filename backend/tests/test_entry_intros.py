from backend.tailor_cv import entry_intro_findings, with_master_entry_intros

MASTER = """# Serghei Granici

## Berufserfahrung

### Product Designer — CorLab (Praktikum)

_05/2026 – heute_

Eigenverantwortliche Leitung von Projekten – von der Anforderungsanalyse bis zur Umsetzung.

**Verwaltungssystem:**

- Use Cases

### Senior UI/UX Designer — dilotec GmbH, Köln

_03/2020 – 07/2025_

- Designsysteme

## Projekte

### CRM-Digest-Bot

_09/2026 – heute_

_Tags: engineering, ai_

Telegram-Bot, der Berichte aus dem CRM automatisch schickt.

- Berichte

## Ausbildung

### Weiterbildung

_2025_

Praktische Projekte.
"""


def _cv(corlab_intro, bot_intro, dilotec_intro=None):
    corlab = f"{corlab_intro}\n\n" if corlab_intro else ""
    dilotec = f"{dilotec_intro}\n\n" if dilotec_intro else ""
    bot = f"{bot_intro}\n\n" if bot_intro else ""
    return (
        "# Serghei Granici\n\n## Berufserfahrung\n\n### Product Designer — CorLab (Praktikum)\n\n"
        f"_05/2026 – heute_\n\n{corlab}**Verwaltungssystem:**\n\n- Use Cases\n\n"
        f"### Senior UI/UX Designer — dilotec GmbH, Köln\n\n_03/2020 – 07/2025_\n\n{dilotec}- Designsysteme\n\n"
        f"## Projekte\n\n### CRM-Digest-Bot\n\n_09/2026 – heute_\n\n{bot}- Berichte\n\n"
        "## Ausbildung\n\n### Weiterbildung\n\n_2025_\n\nPraktische Projekte, neu formuliert.\n"
    )


EXPECTED = _cv(
    "Eigenverantwortliche Leitung von Projekten – von der Anforderungsanalyse bis zur Umsetzung.",
    "Telegram-Bot, der Berichte aus dem CRM automatisch schickt.",
)


def test_reworded_introductions_are_put_back_word_for_word():
    reworded = _cv("Projekte eigenverantwortlich geleitet.", "Ein Telegram-Bot für CRM-Berichte.")

    assert with_master_entry_intros(reworded, MASTER) == EXPECTED
    assert entry_intro_findings(EXPECTED, MASTER) == []


def test_a_dropped_introduction_comes_back_and_an_invented_one_goes():
    rebuilt = with_master_entry_intros(_cv(None, None, dilotec_intro="Fünf Jahre Designarbeit."), MASTER)

    assert rebuilt == EXPECTED


def test_the_education_section_is_not_touched():
    assert "Praktische Projekte, neu formuliert." in with_master_entry_intros(EXPECTED, MASTER)


def test_a_reworded_introduction_is_reported():
    findings = entry_intro_findings(_cv("Projekte eigenverantwortlich geleitet.", None), MASTER)

    assert findings == [
        "The introduction of 'Product Designer — CorLab (Praktikum)' must be the master CV's, word for word: "
        "Eigenverantwortliche Leitung von Projekten – von der Anforderungsanalyse bis zur Umsetzung.",
        "The introduction of 'CRM-Digest-Bot' must be the master CV's, word for word: "
        "Telegram-Bot, der Berichte aus dem CRM automatisch schickt.",
    ]


def test_a_heading_the_master_does_not_have_is_left_alone_and_reported():
    renamed = EXPECTED.replace("### CRM-Digest-Bot", "### Reporting-Bot")

    assert with_master_entry_intros(renamed, MASTER) == renamed
    assert entry_intro_findings(renamed, MASTER) == [
        "The entry 'Reporting-Bot' is not headed as in the master CV. Keep each experience "
        "and project heading exactly as the master CV writes it."
    ]


def test_a_heading_with_another_dash_still_matches():
    other_dash = _cv("Anders.", None).replace("Product Designer — CorLab", "Product Designer - CorLab")

    assert "Eigenverantwortliche Leitung" in with_master_entry_intros(other_dash, MASTER)


def test_a_role_cut_to_one_line_with_its_dates_still_matches():
    collapsed = EXPECTED.replace(
        "### Senior UI/UX Designer — dilotec GmbH, Köln\n\n_03/2020 – 07/2025_\n\n- Designsysteme\n",
        "### Senior UI/UX Designer — dilotec GmbH, Köln (03/2020 – 07/2025)\n",
    )

    assert entry_intro_findings(collapsed, MASTER) == []
