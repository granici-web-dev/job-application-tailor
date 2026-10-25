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

from backend.errors import FactCheckError
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


CV_MARKDOWN = "# Ivan Petrov\n\n## Summary\nSenior Backend Engineer with Python and FastAPI."
LETTER_MARKDOWN = "Dear Acme GmbH team,\n\nKind regards,\nIvan"


def _client():
    client = Mock()
    client.messages.create.side_effect = [
        _message(ANALYSIS_JSON),
        _message(CV_MARKDOWN),
        _message(CV_MARKDOWN),
        _message(LETTER_MARKDOWN),
        _message(LETTER_MARKDOWN),
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
    assert letter_draft.endswith("Dear Acme GmbH team,\n\nKind regards,\nIvan")

    assert result.tracker_path == tmp_path / "applications_tracker.xlsx"
    assert result.tracker_row == 2
    sheet = load_workbook(result.tracker_path).active
    assert sheet["A2"].value == "Acme GmbH"
    assert sheet["C2"].value == "https://example.com/jobs/1"

    text = "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(result.cv_pdf_path.read_bytes())).pages)
    assert "Senior Backend Engineer" in text


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
        "# Ivan Petrov\n\n## Profil\nBackend Engineer.\n\n"
        "## Berufserfahrung\n- Python, FastAPI\n\n## Ausbildung\n- Weiterbildung\n"
    )
    client = Mock()
    client.messages.create.side_effect = [
        _message(analysis),
        _message(cv),
        _message(cv),
        _message(LETTER_MARKDOWN),
        _message(LETTER_MARKDOWN),
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

## Summary
Backend engineer.

## Skills
Python, FastAPI

## Experience

### Backend Engineer — DataForge GmbH, Berlin

_2021 – heute_

- Built REST services in Python with FastAPI
"""

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
    invented = SHORT_MASTER.replace("with FastAPI", "with FastAPI for 99 clients")
    client = _client_returning(
        invented, invented, SHORT_MASTER, SHORT_MASTER, LETTER_MARKDOWN, LETTER_MARKDOWN
    )

    result = _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    retry_request = _user_messages(client)[3]
    assert "## Fact check" in retry_request
    assert "The number 99" in retry_request
    assert "99" not in (result.company_dir / "_drafts" / "cv.md").read_text(encoding="utf-8")


def test_a_cv_that_fails_the_fact_check_three_times_stops_the_pipeline(tmp_path):
    invented = SHORT_MASTER.replace("with FastAPI", "with FastAPI for 99 clients")
    client = _client_returning(*[invented] * 6)

    with pytest.raises(FactCheckError, match="The number 99 does not appear in the master CV"):
        _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    assert client.messages.create.call_count == 7
    assert not (tmp_path / "out").exists()


def test_a_letter_that_fails_the_fact_check_three_times_stops_the_pipeline(tmp_path):
    bad_letter = "Dear Acme GmbH team,\n\nAt DataForge GmbH I served 99 clients.\n\nKind regards,\nIvan"
    client = _client_returning(SHORT_MASTER, SHORT_MASTER, *[bad_letter] * 6)

    with pytest.raises(FactCheckError, match="cover letter"):
        _run(tmp_path, _profile_dir_with_master(tmp_path, SHORT_MASTER), client)

    assert not (tmp_path / "out").exists()
