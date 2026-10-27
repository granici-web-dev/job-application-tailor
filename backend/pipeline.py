from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from anthropic import Anthropic

from backend.analyze import analyze_job, names_a_position
from backend.errors import FactCheckError, JobTitleMissingError
from backend.factcheck import check_cv, check_letter, fact_check_correction
from backend.fetch import fetch_job_text
from backend.grounding import skill_group_findings, with_master_skill_groups
from backend.headline import (
    application_line_findings,
    cv_language,
    default_headline,
    headline_findings,
    position_name,
    read_headline,
    with_application_line,
    without_application_line,
)
from backend.humanize import humanize
from backend.models import JobAnalysis
from backend.profile import load_photo_bytes, load_profile
from backend.page_limit import fit_to_page_limit
from backend.render_pdf import (
    CvLayout,
    cv_css,
    render_markdown_to_pdf,
    render_markdown_with_page_count,
    section_page_spans,
)
from backend.tailor_cv import (
    apply_position_headline,
    education_findings,
    entry_intro_findings,
    move_skills_after_experience,
    put_back_master_education,
    put_back_master_summary,
    split_off_education,
    split_off_summary,
    summary_variant,
    project_letter_sentence,
    tailor_cv,
    with_master_bullets,
    with_master_entry_intros,
    with_relevant_projects,
    with_summary_variant,
)
from backend.tailor_letter import (
    build_letterhead,
    changed_sentence_findings,
    parse_letter_template,
    restore_template_paragraph,
    company_sentence,
    tailor_letter,
    template_findings,
    unsolicited_intro_findings,
    with_project_sentence,
)
from backend.tracker import append_application
from backend.utils import cover_letter_filename, cv_filename, resolve_unique_company_dir

logger = logging.getLogger(__name__)

TRACKER_FILENAME = "applications_tracker.xlsx"
DRAFTS_DIRNAME = "_drafts"
MAX_FACT_CHECK_RETRIES = 2


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
    job_title: str | None = None,
) -> PipelineResult:
    if job_text is None:
        logger.info("Fetching job posting from %s", job_url)
        job_text = fetch_job_text(job_url)

    logger.info("Analyzing job posting")
    analysis = analyze_job(job_text, client=client, model=model)
    # A position entered by hand for a posting that names none: an unsolicited application.
    unsolicited = bool(job_title and job_title.strip()) and not names_a_position(analysis.job_title)
    if job_title and job_title.strip():
        analysis = replace(analysis, job_title=job_title.strip())
    elif not names_a_position(analysis.job_title):
        # Never a page title or a guess in its place: the position goes on the CV and the letter.
        logger.warning("The posting names no position (%r); asking for one", analysis.job_title)
        raise JobTitleMissingError()

    logger.info("Loading profile from %s", profile_dir)
    profile = load_profile(profile_dir)
    logger.info("Using the '%s' summary for discipline '%s'", summary_variant(analysis.discipline), analysis.discipline)
    master_cv_markdown = with_summary_variant(profile.master_cv_markdown, analysis.discipline)
    # The letter's master keeps every project, so the fact check knows each one; its project
    # paragraph tells the one the CV leads its Projekte with.
    profile = replace(
        profile,
        master_cv_markdown=with_relevant_projects(master_cv_markdown, None),
        cover_letter_template=with_project_sentence(
            profile.cover_letter_template, project_letter_sentence(master_cv_markdown, analysis.discipline)
        ),
    )
    cv_profile = replace(
        profile, master_cv_markdown=with_relevant_projects(master_cv_markdown, analysis.discipline)
    )

    logger.info("Tailoring CV and cover letter for %s", analysis.company_name)
    posting_terms = analysis.hard_skills + analysis.keywords
    # Data the documents may quote that is not in the master CV, so its numbers are not findings.
    allowed_text = "\n".join(
        [profile.personal.as_contact_lines(), analysis.job_title or "", analysis.company_name or ""]
    )
    # A posting term inside these is the posting quoted, not a skill claimed.
    # Its form without the gender marker too: the headline and the application line quote it so.
    posting_names = [analysis.job_title or "", position_name(analysis.job_title), analysis.company_name or ""]
    photo = load_photo_bytes(profile.personal.photo_path)

    headline_misses = 0
    group_misses = 0

    def draft_cv(feedback: str | None) -> str:
        nonlocal headline_misses, group_misses
        cv = tailor_cv(analysis, cv_profile, client=client, model=model, language=language, feedback=feedback)
        headline = read_headline(cv)
        # The summary is the master CV's paragraph, untouched by humanize; the fact check
        # still reads it, since it runs on the whole CV.
        cv, summary = split_off_summary(cv)
        # The education likewise: the master CV's section, word for word, never humanized.
        cv, education, after_education = split_off_education(cv)
        cv = humanize(cv, kind="cv", client=client, model=model)
        cv = put_back_master_summary(cv, summary, cv_profile.master_cv_markdown)
        cv = put_back_master_education(cv, education, after_education, cv_profile.master_cv_markdown)
        # Same for each entry's introduction: the master's own paragraph, whatever humanize did.
        cv = with_master_entry_intros(cv, cv_profile.master_cv_markdown)
        # And each entry's bullets: the master's set, in the model's order where it kept them.
        cv = with_master_bullets(cv, cv_profile.master_cv_markdown)
        if headline_findings(headline, job_title=analysis.job_title, language=cv_language(cv)):
            headline_misses += 1
            # One retry for the headline; after that the discipline's default stands in for it
            # rather than failing a CV whose only fault is its headline.
            if headline_misses > 1:
                logger.warning("The CV headline left the role list twice; using the default for %s", analysis.discipline)
                headline = default_headline(analysis.discipline, cv_language(cv), analysis.job_title)
        if headline:
            cv = apply_position_headline(cv, headline)
        cv = with_application_line(cv, analysis.job_title)
        if skill_group_findings(cv, cv_profile.master_cv_markdown):
            group_misses += 1
            # Same bargain as the headline: one retry, then the master CV's groups as they stand.
            if group_misses > 1:
                logger.warning("The CV's skill groups left the master CV's twice; using the master's groups")
                cv = with_master_skill_groups(cv, cv_profile.master_cv_markdown)
        return cv

    def check_cv_facts(cv: str) -> list[str]:
        # The default is a listed headline by construction, so it is not held to the
        # posting's role coming first.
        headline = (
            []
            if headline_misses > 1
            else headline_findings(read_headline(cv), job_title=analysis.job_title, language=cv_language(cv))
        )
        groups = [] if group_misses > 1 else skill_group_findings(cv, cv_profile.master_cv_markdown)
        # The application line is held to the analysis' title alone, not to the master CV.
        intros = entry_intro_findings(cv, cv_profile.master_cv_markdown) + education_findings(
            cv, cv_profile.master_cv_markdown
        )
        return headline + groups + intros + application_line_findings(cv, analysis.job_title) + check_cv(
            without_application_line(cv),
            cv_profile.master_cv_markdown,
            posting_terms=posting_terms,
            allowed_text=allowed_text,
            posting_names=posting_names,
        )

    def finish_cv(cv: str) -> str:
        # After humanize, which rejects a candidate whose headings moved — including ours.
        return move_skills_after_experience(cv)

    def render_cv(cv: str, layout: CvLayout) -> tuple[bytes, int]:
        return render_markdown_with_page_count(
            cv, css=cv_css(layout), photo=photo, include_photo=include_photo, line_breaks=True
        )

    def locate_sections(cv: str, layout: CvLayout) -> list[tuple[int, int]]:
        return section_page_spans(
            cv, css=cv_css(layout), photo=photo, include_photo=include_photo, line_breaks=True
        )

    fitted = fit_to_page_limit(
        finish_cv(_fact_checked(draft_cv, check_cv_facts, kind="CV")), render_cv, posting_terms, locate_sections
    )
    cv_markdown, cv_pdf = fitted.markdown, fitted.pdf

    # No humanize pass on the letter: all but the opening and one sentence are the candidate's
    # own template, which a rewrite could only move away from.
    letter_template = parse_letter_template(profile.cover_letter_template)

    sentence_misses = 0

    def draft_letter(feedback: str | None) -> str:
        nonlocal sentence_misses
        letter = tailor_letter(
            analysis,
            profile,
            client=client,
            model=model,
            feedback=feedback,
            company_page=job_text if unsolicited else None,
        )
        if changed_sentence_findings(letter, letter_template, analysis, profile.master_cv_markdown):
            sentence_misses += 1
            # One retry for the changed sentence; after that the template's own paragraph
            # stands in for it rather than failing a letter whose only fault is style.
            if sentence_misses > 1:
                logger.warning("The changed CorLab sentence missed its limits twice; using the template paragraph")
                letter = restore_template_paragraph(letter, letter_template, analysis)
        return letter

    def check_letter_body(letter: str) -> list[str]:
        opening = unsolicited_intro_findings(letter, analysis) if unsolicited else []
        # In an unsolicited application the opening's second sentence quotes the company's page.
        names = posting_names + [company_sentence(letter)] if unsolicited else posting_names
        return template_findings(letter, letter_template, analysis) + changed_sentence_findings(
            letter, letter_template, analysis, profile.master_cv_markdown
        ) + opening + check_letter(
            letter,
            profile.master_cv_markdown,
            posting_terms=posting_terms,
            allowed_text=allowed_text,
            posting_names=names,
        )

    cover_letter_markdown = _fact_checked(draft_letter, check_letter_body, kind="cover letter")
    logger.info("Cover letter body has %d words", len(cover_letter_markdown.split()))
    # The letterhead is built from data and goes on after the check, which reads the body only.
    cover_letter_markdown = (
        build_letterhead(profile.personal, analysis, today=today, letter_body=cover_letter_markdown)
        + cover_letter_markdown
    )

    logger.info("Rendering the cover letter")
    cover_letter_pdf = render_markdown_to_pdf(cover_letter_markdown, line_breaks=True)

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
    tracker_row = append_application(
        tracker_path,
        analysis,
        job_url=job_url,
        created_on=today,
        cv_file=f"{company_dir.name}/{cv_pdf_path.name}",
        cover_letter_file=f"{company_dir.name}/{cover_letter_pdf_path.name}",
        location=analysis.location,
    )
    logger.info("Appended tracker row %d", tracker_row)

    return PipelineResult(
        analysis=analysis,
        company_dir=company_dir,
        cv_pdf_path=cv_pdf_path,
        cover_letter_pdf_path=cover_letter_pdf_path,
        tracker_path=tracker_path,
        tracker_row=tracker_row,
    )


def _fact_checked(
    draft: Callable[[str | None], str],
    check: Callable[[str], list[str]],
    *,
    kind: str,
) -> str:
    """A draft that passes the fact check, or FactCheckError — never a draft that fails it.

    Each failed attempt is retried with its findings attached, up to MAX_FACT_CHECK_RETRIES
    times.
    """
    feedback: str | None = None
    findings: list[str] = []
    attempts = MAX_FACT_CHECK_RETRIES + 1
    for attempt in range(1, attempts + 1):
        text = draft(feedback)
        findings = check(text)
        if not findings:
            if attempt > 1:
                logger.info("The %s passed the fact check on attempt %d", kind, attempt)
            return text
        logger.warning(
            "The %s failed the fact check on attempt %d of %d:\n- %s",
            kind, attempt, attempts, "\n- ".join(findings),
        )
        feedback = fact_check_correction(findings)
    raise FactCheckError(
        f"The {kind} still states things the master CV does not back after {attempts} attempts, "
        "so no documents were written:\n- " + "\n- ".join(findings)
    )


