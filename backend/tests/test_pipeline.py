import io
import json
import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pypdf
import pytest
from openpyxl import load_workbook

from backend.errors import FactCheckError, JobTitleMissingError
from backend.pipeline import run_pipeline
from backend.tracker import read_applications

PROFILE_DIR = Path(__file__).parent / "fixtures" / "profile"

ANALYSIS_JSON = json.dumps(
    {
        "company_name": "Acme GmbH",
        "job_title": "Senior Backend Engineer",
        "employment_type": "remote",
        "employee_count": None,
        "location": "Wien, Österreich",
        "hard_skills": ["Python", "FastAPI"],
        "keywords": ["Python"],
    }
)


def _message(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


CV_MARKDOWN = "# Ivan Petrov\n\n**Design Engineer · Full-Stack Developer**\n\n## Summary\nSenior Backend Engineer with Python and FastAPI."
LETTER_JSON = json.dumps(
    {
        "salutation": "Dear Hiring Team,",
        "intro": "I read your posting for Senior Backend Engineer at Acme GmbH with great interest.",
        "adjusted_paragraph": (
            "At DataForge GmbH I build REST APIs in Python with FastAPI. I also design PostgreSQL schemas."
        ),
    }
)


def _client():
    client = Mock()
    client.messages.create.side_effect = [
        _message(ANALYSIS_JSON),
        _message(CV_MARKDOWN),
        _message(CV_MARKDOWN),
        _message(LETTER_JSON),
    ]
    return client


def test_run_pipeline_writes_pdfs_drafts_and_tracker_row(tmp_path):
    result = run_pipeline(
        job_url="https://example.com/jobs/1",
        job_text="Senior Backend Engineer at Acme GmbH. Python, FastAPI.",
        output_dir=tmp_path,
        profile_dir=PROFILE_DIR,
        client=_client(),
        model="claude-sonnet-4-6",
        language=None,
        today=date(2026, 6, 1),
    )

    assert result.company_dir == tmp_path / "Acme_GmbH"
    assert result.cv_pdf_path.name == "CV_Ivan_Petrov_Acme_GmbH.pdf"
    assert result.cover_letter_pdf_path.name == "CoverLetter_Ivan_Petrov_Acme_GmbH.pdf"
    assert result.cv_pdf_path.read_bytes().startswith(b"%PDF")
    assert result.cover_letter_pdf_path.read_bytes().startswith(b"%PDF")

    drafts = result.company_dir / "_drafts"
    assert (drafts / "cv.md").read_text(encoding="utf-8").startswith("# Ivan Petrov")
    letter_draft = (drafts / "cover_letter.md").read_text(encoding="utf-8")
    assert letter_draft.startswith('<p class="letter-sender">Ivan Petrov<br>Siegburg, Germany')
    assert '<p class="letter-subject">Application for Senior Backend Engineer</p>' in letter_draft
    assert "Dear Hiring Team,\n\nI read your posting for Senior Backend Engineer" in letter_draft
    assert "glad to join Acme GmbH.\n\nKind regards,\nIvan Petrov" in letter_draft

    assert result.tracker_path == tmp_path / "applications_tracker.xlsx"
    assert result.tracker_row == 2
    sheet = load_workbook(result.tracker_path).active
    assert sheet["A2"].value == "Acme GmbH"
    assert sheet["C2"].value == "https://example.com/jobs/1"

    text = "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(result.cv_pdf_path.read_bytes())).pages)
    assert "Design Engineer · Full-Stack Developer" in text


def test_run_pipeline_collision_creates_suffixed_dir(tmp_path):
    shared = dict(
        job_url="https://example.com/jobs/1",
        job_text="job text",
        output_dir=tmp_path,
        profile_dir=PROFILE_DIR,
        model="claude-sonnet-4-6",
        language=None,
        today=date(2026, 6, 1),
    )

    first = run_pipeline(client=_client(), **shared)
    second = run_pipeline(client=_client(), **shared)

    assert first.company_dir == tmp_path / "Acme_GmbH"
    assert second.company_dir == tmp_path / "Acme_GmbH_2"
    assert second.tracker_row == 3

    applications = read_applications(tmp_path / "applications_tracker.xlsx")
    assert applications[0].cv_file.startswith("Acme_GmbH/")
    assert applications[1].cv_file.startswith("Acme_GmbH_2/")
    assert applications[0].location == "Wien, Österreich"


def _images(pdf_path):
    reader = pypdf.PdfReader(io.BytesIO(pdf_path.read_bytes()))
    return [image for page in reader.pages for image in page.images]


def _profile_dir_with_photo(tmp_path, photo_bytes):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    for name in ("master_cv.md", "cover_letter_template.md", "personal.json"):
        shutil.copy(PROFILE_DIR / name, profile_dir / name)
    (profile_dir / "photo.jpg").write_bytes(photo_bytes)
    return profile_dir


def test_run_pipeline_embeds_photo_when_present(tmp_path, tiny_jpeg):
    profile_dir = _profile_dir_with_photo(tmp_path, tiny_jpeg)

    result = run_pipeline(
        job_url="https://example.com/jobs/1",
        job_text="Senior Backend Engineer at Acme GmbH.",
        output_dir=tmp_path / "out",
        profile_dir=profile_dir,
        client=_client(),
        model="claude-sonnet-4-6",
        language=None,
        today=date(2026, 6, 1),
    )

    assert len(_images(result.cv_pdf_path)) >= 1
    assert _images(result.cover_letter_pdf_path) == []


def test_run_pipeline_without_photo_file_succeeds(tmp_path):
    result = run_pipeline(
        job_url="https://example.com/jobs/1",
        job_text="Senior Backend Engineer at Acme GmbH.",
        output_dir=tmp_path / "out",
        profile_dir=PROFILE_DIR,
        client=_client(),
        model="claude-sonnet-4-6",
        language=None,
        today=date(2026, 6, 1),
    )

    assert result.cv_pdf_path.read_bytes().startswith(b"%PDF")
    assert _images(result.cv_pdf_path) == []


def test_education_stays_below_experience_on_an_engineering_posting(tmp_path):
    analysis = json.dumps({**json.loads(ANALYSIS_JSON), "discipline": "engineering"})
    cv = (
        "# Ivan Petrov\n\n**Design Engineer · Fullstack-Entwickler**\n\n## Profil\nBackend Engineer.\n\n"
        "## Berufserfahrung\n- Python, FastAPI\n\n## Ausbildung\n- Weiterbildung\n"
    )
    client = Mock()
    client.messages.create.side_effect = [
        _message(analysis),
        _message(cv),
        _message(cv),
        _message(LETTER_JSON),
    ]

    result = run_pipeline(
        job_url="https://example.com/jobs/1",
        job_text="Senior Backend Engineer at Acme GmbH.",
        output_dir=tmp_path,
        profile_dir=PROFILE_DIR,
        client=client,
        model="claude-sonnet-4-6",
        language=None,
        today=date(2026, 6, 1),
    )

    draft = (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")
    assert draft.index("## Berufserfahrung") < draft.index("## Ausbildung")


SHORT_MASTER = """# Ivan Petrov

**Design Engineer · Full-Stack Developer**

## Summary
Backend engineer.

## Skills
Python, FastAPI

## Experience

### Backend Engineer — DataForge GmbH, Berlin

_2021 – heute_

- Built REST services in Python with FastAPI
"""

def _long_role(title, dates, count):
    return f"\n### {title}\n\n_{dates}_\n\n" + "\n".join(
        f"- Wartung von Altsystem Nummer {number}" for number in range(1, count + 1)
    ) + "\n"


def _profile_dir_with_master(tmp_path, master):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    for name in ("cover_letter_template.md", "personal.json"):
        shutil.copy(PROFILE_DIR / name, profile_dir / name)
    (profile_dir / "master_cv.md").write_text(master, encoding="utf-8")
    return profile_dir


def _client_returning(*texts):
    client = Mock()
    client.messages.create.side_effect = [_message(ANALYSIS_JSON)] + [_message(text) for text in texts]
    return client


def _user_messages(client):
    return [call.kwargs["messages"][0]["content"] for call in client.messages.create.call_args_list]


def _run(tmp_path, profile_dir, client):
    return run_pipeline(
        job_url="https://example.com/jobs/1",
        job_text="Senior Backend Engineer at Acme GmbH.",
        output_dir=tmp_path / "out",
        profile_dir=profile_dir,
        client=client,
        model="claude-sonnet-4-6",
        language=None,
        today=date(2026, 6, 1),
    )


def test_a_cv_that_fails_the_fact_check_is_retried_with_the_findings(tmp_path):
    # Outside the experience: a bullet there is put back from the master before the check.
    invented = SHORT_MASTER + "\n## Awards\n\n- Winner of 99 hackathons\n"
    client = _client_returning(
        invented, invented, SHORT_MASTER, SHORT_MASTER, LETTER_JSON
    )

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    retry_request = _user_messages(client)[3]
    assert "## Fact check" in retry_request
    assert "The number 99" in retry_request
    assert "99" not in (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")


def test_a_cv_that_fails_the_fact_check_three_times_stops_the_pipeline(tmp_path):
    # Outside the experience: a bullet there is put back from the master before the check.
    invented = SHORT_MASTER + "\n## Awards\n\n- Winner of 99 hackathons\n"
    client = _client_returning(*[invented] * 6)

    with pytest.raises(FactCheckError, match="The number 99 does not appear in the master CV"):
        _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    assert client.messages.create.call_count == 7
    assert not (tmp_path / "out").exists()


def test_a_letter_that_fails_the_fact_check_three_times_stops_the_pipeline(tmp_path):
    bad_letter = json.dumps(
        {**json.loads(LETTER_JSON), "intro": "At DataForge GmbH I served 99 clients."}
    )
    client = _client_returning(SHORT_MASTER, SHORT_MASTER, *[bad_letter] * 3)

    with pytest.raises(FactCheckError, match="cover letter"):
        _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    assert not (tmp_path / "out").exists()


def test_a_cv_over_two_pages_keeps_every_role_and_goes_out_anyway(tmp_path):
    master = SHORT_MASTER + _long_role("Junior Developer — Oldtech AG, Riga", "2010 – 2014", 150)
    client = _client_returning(master, master, LETTER_JSON)

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, master), client)

    assert client.messages.create.call_count == 4
    draft = (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")
    assert "### Junior Developer — Oldtech AG, Riga\n" in draft
    assert "- Wartung von Altsystem Nummer 150\n" in draft
    assert "- Built REST services in Python with FastAPI" in draft
    assert len(pypdf.PdfReader(io.BytesIO(result.cv_pdf_path.read_bytes())).pages) > 2


def _letter_with_corlab_sentence(sentence):
    parts = json.loads(LETTER_JSON)
    parts["adjusted_paragraph"] += " " + sentence
    return json.dumps(parts)


def test_a_changed_sentence_that_misses_its_limits_twice_falls_back_to_the_template(tmp_path):
    dashed = _letter_with_corlab_sentence("I work – mostly – in Python.")
    client = _client_returning(SHORT_MASTER, SHORT_MASTER, dashed, dashed)

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    letter = (result.company_dir / "_drafts" / "cover_letter.md").read_text(encoding="utf-8")
    assert "mostly" not in letter
    assert "I also design PostgreSQL schemas.\n\nBefore that" in letter
    assert client.messages.create.call_count == 5
    assert "sets off an insertion with a dash" in _user_messages(client)[4]


def test_a_changed_sentence_fixed_on_the_retry_is_kept(tmp_path):
    dashed = _letter_with_corlab_sentence("I work – mostly – in Python.")
    fixed = _letter_with_corlab_sentence("I work mostly in Python.")
    client = _client_returning(SHORT_MASTER, SHORT_MASTER, dashed, fixed)

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    letter = (result.company_dir / "_drafts" / "cover_letter.md").read_text(encoding="utf-8")
    assert "I work mostly in Python." in letter



def test_the_summary_is_the_master_paragraph_and_never_reaches_humanize(tmp_path):
    rewritten = SHORT_MASTER.replace("Backend engineer.", "Backend engineer shipping everything to production.")
    client = _client_returning(rewritten, rewritten.replace("## Summary\nBackend engineer shipping everything to production.\n\n", ""), LETTER_JSON)

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    humanize_request = _user_messages(client)[2]
    assert "## Summary" not in humanize_request
    draft = (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")
    assert "## Summary\n\nBackend engineer.\n" in draft
    assert "production" not in draft


def test_a_headline_off_the_role_list_twice_falls_back_to_the_default(tmp_path):
    off_list = SHORT_MASTER.replace(
        "**Design Engineer · Full-Stack Developer**", "**Solution Architect · AI Engineer**"
    )
    client = _client_returning(off_list, off_list, off_list, off_list, LETTER_JSON)

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    assert "'Solution Architect' is not on the allowed list" in _user_messages(client)[3]
    draft = (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")
    assert "Solution Architect" not in draft
    assert draft.startswith("# Ivan Petrov\n\n**Design Engineer · Full-Stack Developer**\n")


def test_a_headline_fixed_on_the_retry_is_kept(tmp_path):
    off_list = SHORT_MASTER.replace(
        "**Design Engineer · Full-Stack Developer**", "**Solution Architect · AI Engineer**"
    )
    fixed = SHORT_MASTER.replace(
        "**Design Engineer · Full-Stack Developer**", "**AI Engineer · Full-Stack Developer**"
    )
    client = _client_returning(off_list, off_list, fixed, fixed, LETTER_JSON)

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    draft = (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")
    assert draft.startswith("# Ivan Petrov\n\n**AI Engineer · Full-Stack Developer**\n")


def test_the_cv_gets_only_the_projects_for_the_discipline_and_the_letter_gets_all(tmp_path):
    master = SHORT_MASTER + (
        "\n## Projects\n\n### Clinic Website\n\n_2026_\n\n_Tags: design_\n\n- Website\n"
        "\n### Report Bot\n\n_2026_\n\n_Tags: engineering, ai_\n\n- Reports\n"
    )
    analysis = json.dumps({**json.loads(ANALYSIS_JSON), "discipline": "ai"})
    client = Mock()
    client.messages.create.side_effect = [
        _message(analysis),
        _message(SHORT_MASTER),
        _message(SHORT_MASTER),
        _message(LETTER_JSON),
    ]

    _run(tmp_path, _profile_dir_with_master(tmp_path, master), client)

    cv_request, letter_request = _user_messages(client)[1], _user_messages(client)[3]
    assert "Report Bot" in cv_request
    assert "Clinic Website" not in cv_request
    assert "Report Bot" in letter_request and "Clinic Website" in letter_request
    assert "_Tags:" not in cv_request + letter_request



GROUPED_MASTER = SHORT_MASTER.replace(
    "## Skills\nPython, FastAPI", "## Skills\n- **Backend:** Python, FastAPI\n- **Tools:** Docker"
)


def test_skill_groups_renamed_twice_fall_back_to_the_master_groups(tmp_path):
    renamed = GROUPED_MASTER.replace("- **Backend:** Python, FastAPI\n- **Tools:** Docker", "**Server:** Python, FastAPI")
    client = _client_returning(renamed, renamed, renamed, renamed, LETTER_JSON)

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, GROUPED_MASTER), client)

    assert "The skill group 'Server' is not one of the master CV's" in _user_messages(client)[3]
    draft = (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")
    assert "**Server:**" not in draft
    assert "- **Backend:** Python, FastAPI\n- **Tools:** Docker" in draft


def test_the_letter_project_paragraph_is_the_sentence_of_the_discipline_project(tmp_path):
    master = SHORT_MASTER + (
        "\n## Projects\n\n### Clinic Website\n\n_2026_\n\n_Tags: design_\n\n"
        "_Letter: I also built a clinic website._\n\n- Website\n"
        "\n### Report Bot\n\n_2026_\n\n_Tags: engineering, ai_\n\n"
        "_Letter: I also built a report bot._\n\n- Reports\n"
    )
    profile_dir = _profile_dir_with_master(tmp_path, master)
    template = (profile_dir / "cover_letter_template.md").read_text(encoding="utf-8")
    (profile_dir / "cover_letter_template.md").write_text(
        template.replace("Flask services at Nordwind AG.", "Flask services at Nordwind AG. [PROJEKT]"), encoding="utf-8"
    )
    analysis = json.dumps({**json.loads(ANALYSIS_JSON), "discipline": "ai"})
    client = Mock()
    client.messages.create.side_effect = [
        _message(analysis),
        _message(SHORT_MASTER),
        _message(SHORT_MASTER),
        _message(LETTER_JSON),
    ]

    result = _run(tmp_path, profile_dir, client)

    letter = (result.company_dir / "_drafts" / "cover_letter.md").read_text(encoding="utf-8")
    assert "Flask services at Nordwind AG. I also built a report bot.\n\n" in letter
    assert "clinic website" not in letter
    assert "_Letter:" not in _user_messages(client)[1] + _user_messages(client)[3]



UNSOLICITED_JSON = json.dumps({**json.loads(ANALYSIS_JSON), "job_title": "Initiativbewerbung"})
UNSOLICITED_LETTER_JSON = json.dumps(
    {
        **json.loads(LETTER_JSON),
        "intro": "Ich bewerbe mich initiativ als Senior Backend Engineer bei der Acme GmbH. Acme GmbH builds software.",
    }
)


@pytest.mark.parametrize("analysis", [UNSOLICITED_JSON, json.dumps({**json.loads(ANALYSIS_JSON), "job_title": None})])
def test_a_posting_without_a_position_stops_before_tailoring(tmp_path, analysis):
    client = Mock()
    client.messages.create.side_effect = [_message(analysis)]

    with pytest.raises(JobTitleMissingError, match="Название позиции не найдено, укажите его вручную"):
        _run(tmp_path, PROFILE_DIR, client)

    assert client.messages.create.call_count == 1
    assert not (tmp_path / "out").exists()


def test_a_position_entered_by_hand_replaces_the_missing_one(tmp_path):
    client = Mock()
    client.messages.create.side_effect = [
        _message(UNSOLICITED_JSON), _message(CV_MARKDOWN), _message(CV_MARKDOWN), _message(UNSOLICITED_LETTER_JSON)
    ]

    result = run_pipeline(
        job_url="https://example.com/jobs/1",
        job_text="Initiativbewerbung bei Acme GmbH.",
        output_dir=tmp_path,
        profile_dir=PROFILE_DIR,
        client=client,
        model="claude-sonnet-4-6",
        language=None,
        today=date(2026, 6, 1),
        job_title="Senior Backend Engineer",
    )

    assert result.analysis.job_title == "Senior Backend Engineer"
    assert "Senior Backend Engineer" in _user_messages(client)[1]


def test_the_cv_names_the_posting_position_under_the_headline(tmp_path):
    result = _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), _client_returning(SHORT_MASTER, SHORT_MASTER, LETTER_JSON))

    draft = (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")
    assert draft.startswith(
        "# Ivan Petrov\n\n**Design Engineer · Full-Stack Developer**\n\nApplication for: Senior Backend Engineer\n"
    )


def test_an_unsolicited_letter_gets_the_company_page_and_its_opening_is_checked(tmp_path):
    vacancy = json.dumps({**json.loads(LETTER_JSON), "intro": "The Stelle at Acme GmbH is interesting."})
    client = Mock()
    client.messages.create.side_effect = [
        _message(UNSOLICITED_JSON), _message(CV_MARKDOWN), _message(CV_MARKDOWN),
        _message(vacancy), _message(vacancy), _message(vacancy),
    ]

    with pytest.raises(FactCheckError, match="Ich bewerbe mich initiativ als Backend Engineer bei Acme GmbH"):
        run_pipeline(
            job_url="https://example.com/jobs/1",
            job_text="Initiativbewerbung bei Acme GmbH. Wir bauen Software für Banken.",
            output_dir=tmp_path,
            profile_dir=PROFILE_DIR,
            client=client,
            model="claude-sonnet-4-6",
            language=None,
            today=date(2026, 6, 1),
            job_title="Backend Engineer",
        )

    letter_request = _user_messages(client)[3]
    assert "## Unsolicited application" in letter_request
    assert "Wir bauen Software für Banken." in letter_request
    assert "'Stelle'" in _user_messages(client)[4]


def test_a_posting_with_its_own_position_gets_no_unsolicited_opening(tmp_path):
    client = _client_returning(SHORT_MASTER, SHORT_MASTER, LETTER_JSON)

    _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    assert "## Unsolicited application" not in _user_messages(client)[3]
