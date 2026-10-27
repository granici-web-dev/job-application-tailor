from backend.emphasis import emphasis_instruction, emphasis_section
from backend.models import JobAnalysis
from backend.profile import PersonalInfo, Profile
from backend.tailor_cv import build_cv_prompt
from backend.tailor_letter import build_letter_prompt, parse_letter_template

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
    cover_letter_template=(
        "[ANREDE]\n\nEinleitung.\n\nAktuell bei CorLab.\n\nAb sofort verfügbar.\n\n"
        "Mit freundlichen Grüßen\nSerghei"
    ),
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


def test_design_posting_keeps_the_training_and_its_stack_to_a_mention():
    cv = emphasis_instruction("design", kind="cv")
    letter = emphasis_instruction("design", kind="cover_letter")

    # The CV thins the enumeration, not the entry, and the skills list leads with design.
    assert "named in passing" in cv
    assert "The entry itself stays" in cv
    assert "put the master CV's design groups first" in cv
    # The letter gives the training a sentence and a handful of technologies, not a paragraph.
    assert "collapses into a single sentence" in letter
    assert "at most four technologies" in letter
    assert "knows both sides" in letter


def test_engineering_posting_still_carries_the_full_stack():
    """The shortening is a design-posting concession; an engineering application keeps everything."""
    for kind in ("cv", "cover_letter"):
        instruction = emphasis_instruction("engineering", kind=kind)

        assert "at most four technologies" not in instruction
        assert "overrides" not in instruction


def test_both_disciplines_group_the_skills_under_category_labels():
    """Same bold form on both sides — it is the one the grounding check knows how to strip."""
    for discipline in ("design", "engineering"):
        assert "`**Label:**`" in emphasis_instruction(discipline, kind="cv")


def test_each_discipline_leads_the_categories_with_its_own_track():
    assert "UI/UX design, usability" in emphasis_instruction("design", kind="cv")
    assert "frontend, backend and APIs" in emphasis_instruction("engineering", kind="cv")


def test_category_labels_never_license_an_empty_group():
    """A label with nothing behind it is the one thing that would pull invented skills in."""
    for discipline in ("design", "engineering"):
        instruction = emphasis_instruction(discipline, kind="cv")

        assert "Only label a group that has skills to hold" in instruction


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


def test_the_letter_prompt_carries_no_emphasis_since_the_template_fixes_the_order():
    template = parse_letter_template(PROFILE.cover_letter_template)

    for discipline in ("design", "engineering"):
        _, user_message = build_letter_prompt(_analysis(discipline), PROFILE, template)
        assert "## Emphasis for this posting" not in user_message


def test_unclassified_posting_leaves_the_prompts_as_they_were():
    _, cv_message = build_cv_prompt(_analysis("unknown", "Projektmanager"), PROFILE)
    _, letter_message = build_letter_prompt(
        _analysis("unknown", "Projektmanager"), PROFILE, parse_letter_template(PROFILE.cover_letter_template)
    )

    assert "## Emphasis for this posting" not in cv_message
    assert "## Emphasis for this posting" not in letter_message


def test_an_ai_posting_gets_the_engineering_emphasis():
    assert emphasis_instruction("ai", kind="cv") == emphasis_instruction("engineering", kind="cv")


def test_cv_emphasis_keeps_the_master_cv_group_labels():
    for discipline in ("design", "engineering"):
        instruction = emphasis_instruction(discipline, kind="cv")

        assert "the master CV's own label in bold, word for word" in instruction
        assert "Never rename, merge or split a group" in instruction
        assert "posting's language" not in instruction

