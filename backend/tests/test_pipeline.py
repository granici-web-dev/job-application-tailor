import io
import json
import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pypdf
from openpyxl import load_workbook

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
    assert (drafts / "cover_letter.md").read_text(encoding="utf-8").startswith("Dear Acme GmbH team,")

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
