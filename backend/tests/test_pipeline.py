import io
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pypdf
from openpyxl import load_workbook

from backend.pipeline import run_pipeline

PROFILE_DIR = Path(__file__).parent / "fixtures" / "profile"

ANALYSIS_JSON = json.dumps(
    {
        "company_name": "Acme GmbH",
        "job_title": "Senior Backend Engineer",
        "employment_type": "remote",
        "employee_count": None,
        "hard_skills": ["Python", "FastAPI"],
        "keywords": ["Python"],
    }
)


def _message(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _client():
    client = Mock()
    client.messages.create.side_effect = [
        _message(ANALYSIS_JSON),
        _message("# Ivan Petrov\n\n## Summary\nSenior Backend Engineer with Python and FastAPI."),
        _message("Dear Acme GmbH team,\n\nKind regards,\nIvan"),
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
