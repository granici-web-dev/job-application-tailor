from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from anthropic import Anthropic

from backend.analyze import analyze_job
from backend.fetch import fetch_job_text
from backend.humanize import humanize
from backend.models import JobAnalysis
from backend.profile import load_photo_bytes, load_profile
from backend.render_pdf import CV_CSS, render_markdown_to_pdf
from backend.tailor_cv import tailor_cv
from backend.tailor_letter import tailor_letter
from backend.tracker import append_application
from backend.utils import cover_letter_filename, cv_filename, resolve_unique_company_dir

logger = logging.getLogger(__name__)

TRACKER_FILENAME = "applications_tracker.xlsx"
DRAFTS_DIRNAME = "_drafts"


@dataclass(frozen=True)
class PipelineResult:
    analysis: JobAnalysis
    company_dir: Path
    cv_pdf_path: Path
    cover_letter_pdf_path: Path
    tracker_path: Path
    tracker_row: int


def run_pipeline(
    *,
    job_url: str,
    job_text: str | None,
    output_dir: Path,
    profile_dir: Path,
    client: Anthropic,
    model: str,
    language: str | None,
    today: date,
    include_photo: bool = True,
) -> PipelineResult:
    if job_text is None:
        logger.info("Fetching job posting from %s", job_url)
        job_text = fetch_job_text(job_url)

    logger.info("Analyzing job posting")
    analysis = analyze_job(job_text, client=client, model=model)

    logger.info("Loading profile from %s", profile_dir)
    profile = load_profile(profile_dir)

    logger.info("Tailoring CV and cover letter for %s", analysis.company_name)
    cv_markdown = tailor_cv(analysis, profile, client=client, model=model, language=language)
    cv_markdown = humanize(cv_markdown, kind="cv", client=client, model=model)
    cover_letter_markdown = tailor_letter(analysis, profile, client=client, model=model, language=language)
    cover_letter_markdown = humanize(cover_letter_markdown, kind="cover_letter", client=client, model=model)

    logger.info("Rendering PDFs")
    photo = load_photo_bytes(profile.personal.photo_path)
    cv_pdf = render_markdown_to_pdf(cv_markdown, css=CV_CSS, photo=photo, include_photo=include_photo)
    cover_letter_pdf = render_markdown_to_pdf(cover_letter_markdown)

    output_dir.mkdir(parents=True, exist_ok=True)
    company_dir = resolve_unique_company_dir(output_dir, analysis.company_name)
    drafts_dir = company_dir / DRAFTS_DIRNAME
    drafts_dir.mkdir(parents=True)

    cv_pdf_path = company_dir / cv_filename(profile.personal.full_name, analysis.company_name)
    cover_letter_pdf_path = company_dir / cover_letter_filename(profile.personal.full_name, analysis.company_name)
    cv_pdf_path.write_bytes(cv_pdf)
    cover_letter_pdf_path.write_bytes(cover_letter_pdf)
    (drafts_dir / "cv.md").write_text(cv_markdown, encoding="utf-8")
    (drafts_dir / "cover_letter.md").write_text(cover_letter_markdown, encoding="utf-8")
    logger.info("Wrote %s and %s", cv_pdf_path.name, cover_letter_pdf_path.name)

    tracker_path = output_dir / TRACKER_FILENAME
    tracker_row = append_application(tracker_path, analysis, job_url=job_url, created_on=today)
    logger.info("Appended tracker row %d", tracker_row)

    return PipelineResult(
        analysis=analysis,
        company_dir=company_dir,
        cv_pdf_path=cv_pdf_path,
        cover_letter_pdf_path=cover_letter_pdf_path,
        tracker_path=tracker_path,
        tracker_row=tracker_row,
    )
