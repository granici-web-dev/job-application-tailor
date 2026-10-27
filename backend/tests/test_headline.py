from backend.headline import (
    application_line_findings,
    cv_language,
    default_headline,
    headline_findings,
    position_name,
    posting_title,
    read_headline,
    with_application_line,
    without_application_line,
)

GERMAN_CV = "# Serghei Granici\n\n**{}**\n\nWacholderweg 6\n\n## Profil\n\nText.\n"


def _findings(headline, job_title="Senior UX Designer (m/w/d)", language="de"):
    return headline_findings(headline, job_title=job_title, language=language)


def test_a_listed_headline_passes():
    assert _findings("Senior UI/UX Designer · Design Engineer") == []


def test_a_role_outside_the_list_is_caught():
    findings = _findings("Solution Architect · Design Engineer", job_title="Solution Architect (m/w/d)")

    assert len(findings) == 1
    assert findings[0].startswith("The headline role 'Solution Architect' is not on the allowed list")


def test_senior_on_a_development_role_is_caught():
    assert _findings("Senior Frontend-Entwickler · Design Engineer")[0].startswith(
        "The headline role 'Senior Frontend-Entwickler'"
    )


def test_the_english_form_on_a_german_cv_is_caught():
    assert _findings("Design Engineer · Full-Stack Developer")[0].startswith(
        "The headline role 'Full-Stack Developer'"
    )


def test_one_or_four_roles_are_caught():
    assert "1 roles" in _findings("Design Engineer")[0]
    assert "4 roles" in _findings(
        "Design Engineer · Fullstack-Entwickler · Frontend-Entwickler · AI Engineer"
    )[0]


def test_a_title_containing_a_listed_role_comes_first_whole():
    title = "Senior Frontend Developer (m/w/d) React"

    assert _findings("Senior Frontend Developer React · Design Engineer · Fullstack-Entwickler", job_title=title) == []
    assert _findings("Frontend-Entwickler · Design Engineer", job_title=title) == [
        "The posting's title contains a listed role, so the headline starts with the title as it "
        "stands: 'Senior Frontend Developer React'."
    ]


def test_the_roles_after_the_title_come_from_the_list_and_do_not_repeat_it():
    title = "Frontend Developer (m/w/d) React / TypeScript"

    findings = _findings("Frontend Developer React / TypeScript · Frontend-Entwickler · Solution Architect", job_title=title)

    assert findings[0].startswith("The headline role 'Solution Architect' is not on the allowed list")
    assert findings[1] == (
        "The headline role 'Frontend-Entwickler' repeats the role in the title 'Frontend Developer React / TypeScript'."
    )


def test_a_title_without_a_listed_role_keeps_the_headline_from_the_list():
    assert posting_title("Senior UX Designer (m/w/d)") is None
    assert _findings("Senior UI/UX Designer · Design Engineer", job_title="Senior UX Designer (m/w/d)") == []
    assert _findings("Senior UX Designer · Design Engineer", job_title="Senior UX Designer (m/w/d)")[0].startswith(
        "The headline role 'Senior UX Designer' is not on the allowed list"
    )


def test_a_title_entered_by_hand_follows_the_same_rule():
    assert posting_title("Fullstack-Entwickler") == "Fullstack-Entwickler"
    assert _findings("Fullstack-Entwickler · Design Engineer", job_title="Fullstack-Entwickler") == []


def test_the_default_puts_a_title_with_a_listed_role_first():
    assert default_headline("engineering", "de", "Senior Frontend Developer (m/w/d) React") == (
        "Senior Frontend Developer React · Design Engineer · Fullstack-Entwickler"
    )
    assert default_headline("engineering", "de", "Fullstack-Entwickler") == "Fullstack-Entwickler · Design Engineer"
    assert default_headline("analysis", "de", "Business Analyst Digitale Plattformen (m/w/d)") == (
        "Business Analyst Digitale Plattformen · UI/UX Designer · Fullstack-Entwickler"
    )
    assert default_headline("design", "de", "Senior UX Designer (m/w/d)") == "Senior UI/UX Designer · Design Engineer"
    for title in ("Senior Frontend Developer (m/w/d) React", "Fullstack-Entwickler", "AI Engineer / LLM-Entwickler (m/w/d)"):
        assert _findings(default_headline("ai", "de", title), job_title=title) == []


def test_a_missing_headline_is_caught():
    assert _findings(None)[0].startswith("The CV has no headline under the name.")


def test_the_defaults_are_listed_headlines_in_the_cv_language():
    assert default_headline("engineering", "de") == "Design Engineer · Fullstack-Entwickler"
    assert default_headline("engineering", "en") == "Design Engineer · Full-Stack Developer"
    assert default_headline("design", "de") == "Senior UI/UX Designer · Design Engineer"
    assert default_headline("analysis", "de") == "Business Analyst · UI/UX Designer · Fullstack-Entwickler"
    assert default_headline("unknown", "de") == "Design Engineer · Fullstack-Entwickler"
    for discipline in ("engineering", "design", "analysis"):
        for language in ("de", "en"):
            assert _findings(default_headline(discipline, language), language=language) == []


def test_the_headline_and_language_are_read_from_the_cv():
    cv = GERMAN_CV.format("Design Engineer · Fullstack-Entwickler")

    assert read_headline(cv) == "Design Engineer · Fullstack-Entwickler"
    assert cv_language(cv) == "de"
    assert read_headline("# Serghei Granici\n\nWacholderweg 6\n\n## Profil\n") is None
    assert cv_language("# Ivan Petrov\n\n## Summary\n") == "en"


def test_an_ai_posting_defaults_to_the_ai_headline():
    assert default_headline("ai", "de") == "AI Engineer · Fullstack-Entwickler"
    assert default_headline("ai", "en") == "AI Engineer · Full-Stack Developer"


def test_the_position_loses_only_its_gender_marker():
    assert position_name("Frontend Developer (m/w/d) React / TypeScript") == "Frontend Developer React / TypeScript"
    assert position_name("Senior UX Designer (w/m/d)") == "Senior UX Designer"
    assert position_name("AI Engineer (m/f/d)") == "AI Engineer"
    assert position_name("Business Analyst") == "Business Analyst"


def test_the_application_line_goes_under_the_headline():
    cv = with_application_line(GERMAN_CV.format("Senior UI/UX Designer · Design Engineer"), "Senior UX Designer (m/w/d)")

    assert cv.startswith(
        "# Serghei Granici\n\n**Senior UI/UX Designer · Design Engineer**\n\n"
        "Bewerbung als: Senior UX Designer\n\nWacholderweg 6\n"
    )
    assert application_line_findings(cv, "Senior UX Designer (m/w/d)") == []


def test_an_application_line_already_there_gives_way():
    cv = GERMAN_CV.format("Design Engineer · Fullstack-Entwickler").replace(
        "Wacholderweg", "Bewerbung als: Frontend-Profi\n\nWacholderweg"
    )

    rebuilt = with_application_line(cv, "Frontend Developer (m/w/d)")

    assert "Frontend-Profi" not in rebuilt
    assert rebuilt.count("Bewerbung als: Frontend Developer\n") == 1


def test_an_application_line_off_the_analysis_title_is_caught():
    cv = GERMAN_CV.format("Design Engineer · Fullstack-Entwickler").replace(
        "Wacholderweg", "Bewerbung als: Senior Frontend Developer\n\nWacholderweg"
    )

    assert application_line_findings(cv, "Frontend Developer (m/w/d)") == [
        "The line under the headline must read 'Bewerbung als: Frontend Developer', exactly once; "
        "the CV has ['Bewerbung als: Senior Frontend Developer']."
    ]
    assert application_line_findings(GERMAN_CV.format("Design Engineer"), "Frontend Developer")[0].endswith(
        "the CV has none."
    )


def test_the_fact_check_reads_the_cv_without_the_application_line():
    plain = GERMAN_CV.format("Design Engineer · Fullstack-Entwickler")

    assert without_application_line(with_application_line(plain, "Frontend Developer (m/w/d)")) == plain


def test_an_english_cv_gets_the_english_label():
    cv = with_application_line("# Ivan Petrov\n\n**Design Engineer**\n\n## Summary\n", "Backend Engineer (m/f/d)")

    assert "**Design Engineer**\n\nApplication for: Backend Engineer\n\n## Summary" in cv
