from backend.emphasis import emphasis_instruction, emphasis_section
from backend.models import JobAnalysis
from backend.profile import PersonalInfo, Profile
from backend.tailor_cv import build_cv_prompt
from backend.tailor_letter import build_letter_prompt

PROFILE = Profile(
    personal=PersonalInfo(
        full_name="Serghei Granici",
        email="granici.design@gmail.com",
        phone=None,
        location=None,
        linkedin=None,
        github=None,
        languages=[],
    ),
    master_cv_markdown="## Kenntnisse\nReact, TypeScript, UI/UX Design, Figma",
    cover_letter_template="Sehr geehrte Damen und Herren,\n\nMit freundlichen Grüßen\nSerghei",
)


def _analysis(discipline: str, job_title: str = "Product Designer") -> JobAnalysis:
    return JobAnalysis.from_response_dict(
        {"company_name": "Acme GmbH", "job_title": job_title, "discipline": discipline}
    )


def test_design_posting_puts_design_first_in_both_documents():
    for kind in ("cv", "cover_letter"):
        instruction = emphasis_instruction("design", kind=kind).lower()

        assert "design-first" in instruction or "design first" in instruction


def test_engineering_posting_puts_development_first_in_both_documents():
    for kind in ("cv", "cover_letter"):
        instruction = emphasis_instruction("engineering", kind=kind).lower()

        assert "development-first" in instruction or "development first" in instruction


def test_unclassified_posting_gets_no_emphasis_instruction():
    assert emphasis_instruction("unknown", kind="cv") == ""
    assert emphasis_section("unknown", kind="cover_letter") == []


def test_emphasis_never_licenses_dropping_the_other_track():
    for kind in ("cv", "cover_letter"):
        for discipline in ("design", "engineering"):
            instruction = emphasis_instruction(discipline, kind=kind)

            assert "it does not disappear" in instruction
            assert "Never restate a role's title" in instruction


def test_cv_emphasis_forbids_padding_the_skills_it_promotes():
    for discipline in ("design", "engineering"):
        assert "not licence to expand them" in emphasis_instruction(discipline, kind="cv")


def test_design_posting_reaches_the_cv_prompt():
    _, user_message = build_cv_prompt(_analysis("design"), PROFILE)

    assert "## Emphasis for this posting" in user_message
    assert "design-first" in user_message
    assert "development-first" not in user_message


def test_frontend_posting_reaches_the_cv_prompt_as_development_first():
    _, user_message = build_cv_prompt(_analysis("engineering", "Frontend Developer"), PROFILE)

    assert "development-first" in user_message
    assert "design-first" not in user_message


def test_design_posting_reaches_the_letter_prompt():
    _, user_message = build_letter_prompt(_analysis("design"), PROFILE)

    assert "argue design first" in user_message


def test_engineering_posting_reaches_the_letter_prompt():
    _, user_message = build_letter_prompt(_analysis("engineering", "Fullstack Developer"), PROFILE)

    assert "argue development first" in user_message


def test_unclassified_posting_leaves_the_prompts_as_they_were():
    _, cv_message = build_cv_prompt(_analysis("unknown", "Projektmanager"), PROFILE)
    _, letter_message = build_letter_prompt(_analysis("unknown", "Projektmanager"), PROFILE)

    assert "## Emphasis for this posting" not in cv_message
    assert "## Emphasis for this posting" not in letter_message
