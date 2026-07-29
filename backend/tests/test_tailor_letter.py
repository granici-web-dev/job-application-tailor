from datetime import date

from backend.models import JobAnalysis
from backend.profile import PersonalInfo
from backend.tailor_letter import build_letterhead

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
