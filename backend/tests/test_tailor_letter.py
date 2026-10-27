import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.errors import LLMError, ProfileError
from backend.models import JobAnalysis
from backend.profile import PersonalInfo, Profile
from backend.tailor_letter import (
    assemble_letter,
    build_letterhead,
    build_letter_prompt,
    changed_sentence_findings,
    company_sentence,
    parse_letter_template,
    restore_template_paragraph,
    tailor_letter,
    template_findings,
    unsolicited_intro_findings,
)

GERMAN_BODY = "Sehr geehrte Damen und Herren,\n\nText.\n\nMit freundlichen Grüßen\nSerghei Granici"
ENGLISH_BODY = "Dear Sir or Madam,\n\nText.\n\nKind regards,\nSerghei Granici"

PERSONAL = PersonalInfo(
    full_name="Serghei Granici",
    email="granici.design@gmail.com",
    phone="+49 1727014108",
    location="Wacholderweg 6, 53757 Sankt Augustin",
    linkedin=None,
    github=None,
    languages=[],
    photo_path=None,
)


def _analysis(**overrides):
    defaults = dict(
        company_name="Musterfirma Testwerk GmbH",
        job_title="Frontend Developer (m/w/d)",
        employment_type="onsite",
        employee_count=None,
        location="Köln",
        contact_person=None,
        hard_skills=[],
        soft_skills=[],
        keywords=[],
        key_responsibilities=[],
        language_requirements=[],
    )
    return JobAnalysis(**{**defaults, **overrides})


def test_german_letterhead_carries_sender_recipient_date_and_betreff():
    head = build_letterhead(PERSONAL, _analysis(), today=date(2026, 7, 27), letter_body=GERMAN_BODY)

    assert head.startswith(
        '<p class="letter-sender">Serghei Granici<br>Wacholderweg 6, 53757 Sankt Augustin'
        "<br>+49 1727014108 · granici.design@gmail.com</p>"
    )
    assert '<p class="letter-recipient">Musterfirma Testwerk GmbH<br>Köln</p>' in head
    assert '<p class="letter-date">Sankt Augustin, 27. Juli 2026</p>' in head
    assert '<p class="letter-subject">Bewerbung als Frontend Developer (m/w/d)</p>' in head
    assert head.endswith("\n\n")


def test_english_letter_gets_an_english_subject_and_date():
    head = build_letterhead(PERSONAL, _analysis(), today=date(2026, 7, 27), letter_body=ENGLISH_BODY)

    assert '<p class="letter-subject">Application for Frontend Developer (m/w/d)</p>' in head
    assert "27 July 2026" in head
    assert "Bewerbung" not in head


def test_recipient_carries_a_named_contact_person():
    head = build_letterhead(
        PERSONAL,
        _analysis(contact_person="Frau Sennhenn"),
        today=date(2026, 7, 27),
        letter_body=GERMAN_BODY,
    )

    assert (
        '<p class="letter-recipient">Musterfirma Testwerk GmbH<br>z. Hd. Frau Sennhenn<br>Köln</p>'
        in head
    )


def test_english_recipient_uses_attn():
    head = build_letterhead(
        PERSONAL,
        _analysis(contact_person="Ms Sennhenn"),
        today=date(2026, 7, 27),
        letter_body=ENGLISH_BODY,
    )

    assert "Attn: Ms Sennhenn" in head
    assert "z. Hd." not in head


def test_recipient_omits_an_unknown_location():
    head = build_letterhead(
        PERSONAL, _analysis(location=None), today=date(2026, 7, 27), letter_body=GERMAN_BODY
    )

    assert '<p class="letter-recipient">Musterfirma Testwerk GmbH</p>' in head


def test_ampersand_in_the_job_title_is_escaped():
    head = build_letterhead(
        PERSONAL,
        _analysis(job_title="Frontend Developer – React & TypeScript"),
        today=date(2026, 7, 27),
        letter_body=GERMAN_BODY,
    )

    assert "React &amp; TypeScript" in head
    assert "React & TypeScript" not in head


def test_date_line_falls_back_to_the_bare_date_without_a_sender_location():
    anonymous = PersonalInfo(
        full_name="Serghei Granici",
        email="granici.design@gmail.com",
        phone=None,
        location=None,
        linkedin=None,
        github=None,
        languages=[],
        photo_path=None,
    )

    head = build_letterhead(anonymous, _analysis(), today=date(2026, 7, 27), letter_body=GERMAN_BODY)

    assert '<p class="letter-date">27. Juli 2026</p>' in head
    assert head.startswith('<p class="letter-sender">Serghei Granici<br>granici.design@gmail.com</p>')


TEMPLATE = """<!-- Kommentar. -->

[ANREDE — z. B. „Sehr geehrte Frau Sennhenn,"]

mit großem Interesse habe ich Ihre Ausschreibung als [POSITION] gelesen.

Aktuell verantworte ich bei CorLab Projekte komplett selbst. Für eine staatliche Stelle entwerfe ich ein Verwaltungssystem. Ein zweites System habe ich auditiert.

Davor war ich über zehn Jahre im UI/UX-Design tätig.

Ich bringe mich gerne langfristig bei [UNTERNEHMEN] ein.

Mit freundlichen Grüßen
Serghei Granici"""

CORLAB = (
    "Aktuell verantworte ich bei CorLab Projekte komplett selbst. Für eine staatliche Stelle "
    "entwerfe ich ein Verwaltungssystem. Ein zweites System habe ich auditiert."
)


def _letter(adjusted=CORLAB, intro="Ihre Ausschreibung hat mich angesprochen."):
    return assemble_letter(
        parse_letter_template(TEMPLATE),
        _analysis(),
        salutation="Sehr geehrte Damen und Herren,",
        intro=intro,
        adjusted=adjusted,
    )


def _findings(letter):
    return template_findings(letter, parse_letter_template(TEMPLATE), _analysis())


def test_the_template_splits_into_the_parts_the_letter_is_built_from():
    template = parse_letter_template(TEMPLATE)

    assert template.intro.startswith("mit großem Interesse")
    assert template.adjustable == CORLAB
    assert template.fixed == (
        "Davor war ich über zehn Jahre im UI/UX-Design tätig.",
        "Ich bringe mich gerne langfristig bei [UNTERNEHMEN] ein.",
    )
    assert template.signature == "Mit freundlichen Grüßen\nSerghei Granici"


def test_a_template_without_enough_paragraphs_is_rejected():
    with pytest.raises(ProfileError):
        parse_letter_template("[ANREDE]\n\nText.\n\nGrüße")


def test_the_fixed_paragraphs_go_in_word_for_word_with_placeholders_filled():
    letter = _letter()

    assert letter.startswith("Sehr geehrte Damen und Herren,\n\nIhre Ausschreibung hat mich angesprochen.")
    assert "Ich bringe mich gerne langfristig bei Musterfirma Testwerk GmbH ein." in letter
    assert letter.endswith("Mit freundlichen Grüßen\nSerghei Granici")
    assert _findings(letter) == []


def test_one_added_sentence_in_the_adjustable_paragraph_is_allowed():
    added = CORLAB + " Dabei arbeite ich durchgängig mit Claude Code."
    added_in_between = CORLAB.replace(
        "Verwaltungssystem. Ein", "Verwaltungssystem. Dabei arbeite ich durchgängig mit Claude Code. Ein"
    )

    assert _findings(_letter(adjusted=added)) == []
    assert _findings(_letter(adjusted=added_in_between)) == []


def test_a_replaced_template_sentence_is_caught():
    replaced = CORLAB.replace(
        "Ein zweites System habe ich auditiert.", "Ein zweites System habe ich auditiert und neu gestaltet."
    )

    assert _findings(_letter(adjusted=replaced)) == [
        "In the paragraph starting 'Aktuell verantworte ich bei CorLab Projekte …', the template's sentence "
        "'Ein zweites System habe ich auditiert.' is missing or changed. Every sentence of the template "
        "stays word for word; you may only add one of your own."
    ]


def test_a_dropped_template_sentence_is_caught():
    dropped = CORLAB.replace(" Für eine staatliche Stelle entwerfe ich ein Verwaltungssystem.", "")

    findings = _findings(_letter(adjusted=dropped))

    assert len(findings) == 1
    assert "'Für eine staatliche Stelle entwerfe ich ein Verwaltungssystem.' is missing or changed" in findings[0]


def test_reordered_template_sentences_are_caught():
    reordered = (
        "Aktuell verantworte ich bei CorLab Projekte komplett selbst. Ein zweites System habe ich "
        "auditiert. Für eine staatliche Stelle entwerfe ich ein Verwaltungssystem."
    )

    assert _findings(_letter(adjusted=reordered)) == [
        "In the paragraph starting 'Aktuell verantworte ich bei CorLab Projekte …', the template's "
        "sentences must stay in the template's order."
    ]


def test_two_added_sentences_are_caught():
    adjusted = CORLAB + " Dabei arbeite ich mit Claude Code. Außerdem prüfe ich die Barrierefreiheit."

    assert _findings(_letter(adjusted=adjusted)) == [
        "In the paragraph starting 'Aktuell verantworte ich bei CorLab Projekte …', you added 2 "
        "sentences; add at most 1."
    ]


def test_a_reworded_fixed_paragraph_is_caught():
    letter = _letter().replace("über zehn Jahre", "mehr als zehn Jahre")

    assert _findings(letter) == [
        "The paragraph starting 'Davor war ich über zehn Jahre …' must match the template word for word."
    ]


def test_an_opening_split_into_two_paragraphs_is_caught():
    findings = _findings(_letter(intro="Erster Absatz.\n\nZweiter Absatz."))

    assert len(findings) == 1
    assert "The letter has 7 paragraphs; it must have 6" in findings[0]


def test_a_leftover_placeholder_is_caught():
    findings = _findings(_letter(intro="Ihre Ausschreibung als [POSITION] hat mich angesprochen."))

    assert findings == ["The letter still contains template placeholders: [POSITION]."]


def test_a_letter_over_300_words_is_caught():
    findings = _findings(_letter(intro="Wort " * 300))

    assert len(findings) == 1
    assert "the limit is 300" in findings[0]


def _profile(template=TEMPLATE):
    return Profile(
        master_cv_markdown="# Serghei Granici",
        cover_letter_template=template,
        personal=PERSONAL,
    )


def _client(text):
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
    return client


def test_tailor_letter_assembles_the_model_parts_around_the_template():
    parts = {
        "salutation": "Sehr geehrte Damen und Herren,",
        "intro": "Ihre Ausschreibung hat mich angesprochen.",
        "adjusted_paragraph": CORLAB,
    }
    client = _client("```json\n" + json.dumps(parts) + "\n```")

    letter = tailor_letter(_analysis(), _profile(), client=client, model="m", feedback="## Fact check\n- x")

    assert letter == _letter()
    request = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "## Paragraph you may adjust by one sentence\n" + CORLAB in request
    assert request.endswith("## Fact check\n- x")


def test_tailor_letter_rejects_an_answer_that_is_not_the_three_parts():
    with pytest.raises(LLMError):
        tailor_letter(_analysis(), _profile(), client=_client("Sehr geehrte Damen und Herren, ..."), model="m")


def test_a_template_without_the_company_placeholder_needs_none():
    template_text = TEMPLATE.replace("bei [UNTERNEHMEN]", "in Ihr Team")
    template = parse_letter_template(template_text)
    letter = assemble_letter(
        template, _analysis(), salutation="Sehr geehrte Damen und Herren,", intro="Einleitung.", adjusted=CORLAB
    )

    assert "Ich bringe mich gerne langfristig in Ihr Team ein." in letter
    assert template_findings(letter, template, _analysis()) == []



def _sentence_findings(adjusted):
    return changed_sentence_findings(_letter(adjusted=adjusted), parse_letter_template(TEMPLATE), _analysis())


def test_a_short_changed_sentence_without_a_dash_passes():
    assert _sentence_findings(CORLAB + " Dabei arbeite ich durchgängig mit Claude Code.") == []


def test_the_template_paragraph_itself_passes_even_with_its_own_dashes():
    template = TEMPLATE.replace("Ein zweites System habe ich auditiert.", "Ein zweites System – bestehend – habe ich auditiert.")
    corlab = CORLAB.replace("Ein zweites System habe ich auditiert.", "Ein zweites System – bestehend – habe ich auditiert.")
    letter = assemble_letter(
        parse_letter_template(template), _analysis(), salutation="Hallo,", intro="Einleitung.", adjusted=corlab
    )

    assert changed_sentence_findings(letter, parse_letter_template(template), _analysis()) == []


def test_a_changed_sentence_over_30_words_is_caught():
    long_sentence = "Dabei " + "arbeite " * 30 + "ich."

    findings = _sentence_findings(CORLAB + " " + long_sentence)

    assert findings == [
        "The sentence you changed in the paragraph starting 'Aktuell verantworte ich bei CorLab Projekte …' "
        "has 32 words; the limit is 30."
    ]


def test_a_changed_sentence_with_a_dash_insertion_is_caught():
    findings = _sentence_findings(CORLAB + " Dabei arbeite ich – durchgängig – mit Claude Code.")

    assert len(findings) == 1
    assert "sets off an insertion with a dash" in findings[0]


def test_a_hyphen_inside_a_compound_is_not_a_dash():
    assert _sentence_findings(CORLAB + " Dabei führe ich den WCAG-2.2-AA-Audit durch.") == []


def test_the_template_paragraph_can_be_put_back():
    letter = _letter(adjusted=CORLAB + " Dabei arbeite ich – durchgängig – mit Claude Code.")

    restored = restore_template_paragraph(letter, parse_letter_template(TEMPLATE), _analysis())

    assert restored == _letter()


UNSOLICITED = _analysis(job_title="Fullstack-Entwickler", company_name="Lichtwerk Digital GmbH")


def _letter_opening(intro):
    return f"Sehr geehrte Frau Weber,\n\n{intro}\n\nAktuell verantworte ich Projekte.\n\nMit freundlichen Grüßen\nSerghei Granici"


def test_an_unsolicited_opening_that_speaks_of_the_company_passes():
    letter = _letter_opening(
        "ich bewerbe mich initiativ als Fullstack-Entwickler bei der Lichtwerk Digital GmbH. "
        "Die Agentur entwickelt Webanwendungen und Portale für den Mittelstand."
    )

    assert unsolicited_intro_findings(letter, UNSOLICITED) == []
    assert company_sentence(letter) == "Die Agentur entwickelt Webanwendungen und Portale für den Mittelstand."


def test_an_unsolicited_opening_that_reads_as_a_vacancy_is_caught():
    letter = _letter_opening(
        "die Stelle als Fullstack-Entwickler bei der Lichtwerk Digital GmbH reizt mich. "
        "Die Ausschreibung verbindet Frontend und Backend."
    )

    assert unsolicited_intro_findings(letter, UNSOLICITED) == [
        "The opening paragraph must begin with 'ich bewerbe mich initiativ als Fullstack-Entwickler bei "
        "Lichtwerk Digital GmbH'.",
        "The opening paragraph says 'Ausschreibung'. This is an unsolicited application: there is no "
        "vacancy, so Stelle, Ausschreibung and Position never appear in it.",
        "The opening paragraph says 'Stelle'. This is an unsolicited application: there is no "
        "vacancy, so Stelle, Ausschreibung and Position never appear in it.",
    ]


def test_an_opening_with_a_capital_ich_after_the_salutation_is_caught():
    letter = _letter_opening(
        "Ich bewerbe mich initiativ als Fullstack-Entwickler bei der Lichtwerk Digital GmbH. "
        "Die Agentur entwickelt Webanwendungen."
    )

    assert unsolicited_intro_findings(letter, UNSOLICITED) == [
        "The opening paragraph must begin with 'ich bewerbe mich initiativ als Fullstack-Entwickler bei "
        "Lichtwerk Digital GmbH'."
    ]


def test_a_vacancy_word_inside_a_compound_is_caught_too():
    letter = _letter_opening(
        "ich bewerbe mich initiativ als Fullstack-Entwickler bei der Lichtwerk Digital GmbH. "
        "Eine Stellenanzeige habe ich nicht gefunden, die Positionen sind besetzt."
    )

    assert [finding.split("'")[1] for finding in unsolicited_intro_findings(letter, UNSOLICITED)] == [
        "Positionen",
        "Stellenanzeige",
    ]


def test_the_unsolicited_prompt_carries_the_opening_and_the_company_page():
    profile = Profile(
        personal=PERSONAL,
        master_cv_markdown="# Serghei Granici\n\n## Kenntnisse\n\n- **Frontend:** React\n",
        cover_letter_template=TEMPLATE,
    )
    template = parse_letter_template(TEMPLATE)

    _, plain = build_letter_prompt(UNSOLICITED, profile, template)
    _, unsolicited = build_letter_prompt(UNSOLICITED, profile, template, "Wir sind eine Digitalagentur in Köln.")

    assert "## Unsolicited application" not in plain
    assert "'ich bewerbe mich initiativ als Fullstack-Entwickler bei Lichtwerk Digital GmbH'" in unsolicited
    assert "## The company's page\nWir sind eine Digitalagentur in Köln." in unsolicited


PLACEMENT_MASTER = """# Serghei Granici

## Kenntnisse

- **Qualität:** Cognitive Walkthrough, Accessibility (WCAG 2.2 AA)
- **AI & Tools:** Claude Code

## Berufserfahrung

### Product Designer — CorLab (Praktikum)

_05/2026 – heute_

**Verwaltungssystem für eine staatliche Stelle (Moldau):**

- Cognitive Walkthrough und WCAG-2.2-AA-Audit vor der Umsetzung

**Bestehendes System (Moldau) – Audit und Redesign:**

- UX/UI-Audit: 48 Befunde
"""
WCAG = "Dabei habe ich einen WCAG-2.2-AA-Audit durchgeführt."


def _placement(adjusted):
    return changed_sentence_findings(
        _letter(adjusted=adjusted), parse_letter_template(TEMPLATE), _analysis(), PLACEMENT_MASTER
    )


def test_an_added_sentence_after_its_own_system_passes():
    after_first_system = CORLAB.replace("Verwaltungssystem. Ein", f"Verwaltungssystem. {WCAG} Ein")

    assert _placement(after_first_system) == []


def test_an_added_sentence_after_another_system_is_caught():
    assert _placement(CORLAB + " " + WCAG) == [
        f"The sentence you added, '{WCAG}', is about the system 'Verwaltungssystem für eine staatliche "
        "Stelle (Moldau)', so it goes directly after the template's sentence 'Für eine staatliche Stelle "
        "entwerfe ich ein Verwaltungssystem.'."
    ]


def test_a_sentence_about_no_one_system_goes_after_the_first_sentence():
    general = "Dabei arbeite ich durchgängig mit Claude Code."
    after_first = CORLAB.replace("selbst. Für", f"selbst. {general} Für")

    assert _placement(after_first) == []
    assert _placement(CORLAB + " " + general)[0].endswith(
        "is about the position as a whole, so it goes directly after the template's sentence "
        "'Aktuell verantworte ich bei CorLab Projekte komplett selbst.'."
    )


def test_without_an_added_sentence_there_is_nothing_to_place():
    assert _placement(CORLAB) == []
