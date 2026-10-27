import pytest

from backend.headline import cv_headline, cv_language, default_headline, position_name, posting_title


@pytest.mark.parametrize(
    ("job_title", "headline"),
    [
        ("(Junior) Fullstack Developer (m/w/d)", "(Junior) Fullstack Developer"),
        ("Senior UX Designer", "Senior UX Designer"),
        ("Senior Frontend Developer (m/w/d) React", "Senior Frontend Developer React"),
        ("Werkstudent*in UX Designer (all genders)", "Werkstudent*in UX Designer"),
        ("Lead Product Designer (w/m/d)", "Lead Product Designer"),
        ("Fullstack-Entwickler", "Fullstack-Entwickler"),
    ],
)
def test_a_title_with_a_listed_role_is_the_headline_as_the_posting_writes_it(job_title, headline):
    assert cv_headline(job_title, "engineering", "de") == headline


@pytest.mark.parametrize("job_title", ["Solution Architect", "Scrum Master (m/w/d)", "Senior Backend Engineer"])
def test_a_title_without_a_listed_role_takes_the_disciplines_default(job_title):
    assert posting_title(job_title) is None
    assert cv_headline(job_title, "engineering", "de") == "Design Engineer · Fullstack-Entwickler"
    assert cv_headline(job_title, "analysis", "de") == "Business Analyst · UI/UX Designer · Fullstack-Entwickler"


def test_the_defaults_are_listed_headlines_in_the_cv_language():
    assert default_headline("engineering", "de") == "Design Engineer · Fullstack-Entwickler"
    assert default_headline("engineering", "en") == "Design Engineer · Full-Stack Developer"
    assert default_headline("design", "de") == "Senior UI/UX Designer · Design Engineer"
    assert default_headline("analysis", "de") == "Business Analyst · UI/UX Designer · Fullstack-Entwickler"
    assert default_headline("ai", "en") == "AI Engineer · Full-Stack Developer"
    assert default_headline("unknown", "de") == "Design Engineer · Fullstack-Entwickler"


def test_the_language_is_read_from_the_cv():
    assert cv_language("# Serghei Granici\n\n## Profil\n\nText.\n") == "de"
    assert cv_language("# Ivan Petrov\n\n## Summary\n") == "en"


def test_the_position_loses_only_its_gender_marker():
    assert position_name("Frontend Developer (m/w/d) React / TypeScript") == "Frontend Developer React / TypeScript"
    assert position_name("Senior UX Designer (w/m/d)") == "Senior UX Designer"
    assert position_name("AI Engineer (m/f/d)") == "AI Engineer"
    assert position_name("Business Analyst") == "Business Analyst"
