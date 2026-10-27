from backend.headline import cv_language, default_headline, headline_findings, read_headline

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


def test_a_listed_posting_role_has_to_come_first():
    findings = _findings(
        "Design Engineer · Frontend-Entwickler", job_title="Frontend Developer (m/w/d) React / TypeScript"
    )

    assert findings == [
        "The posting's role is on the allowed list, so the headline starts with 'Frontend-Entwickler'."
    ]
    assert _findings(
        "Frontend-Entwickler · Design Engineer", job_title="Frontend Developer (m/w/d) React / TypeScript"
    ) == []


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
