from __future__ import annotations

import json
import re
from datetime import date
from html import escape
from pathlib import Path

from anthropic import Anthropic

from backend.llm import complete
from backend.models import JobAnalysis
from backend.profile import PersonalInfo, Profile

LETTER_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "tailor_letter.md"
MAX_TOKENS = 1500

GERMAN_MONTHS = (
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)
GERMAN_MARKERS = ("Sehr geehrte", "Mit freundlichen Grüßen", "Guten Tag")
POSTCODE = re.compile(r"^\d{4,6}\s+")


def tailor_letter(
    analysis: JobAnalysis,
    profile: Profile,
    *,
    client: Anthropic,
    model: str,
    language: str | None = None,
) -> str:
    system_prompt, user_message = build_letter_prompt(analysis, profile, language)
    return complete(client, model=model, system=system_prompt, user=user_message, max_tokens=MAX_TOKENS)


def build_letterhead(
    personal: PersonalInfo, analysis: JobAnalysis, *, today: date, letter_body: str
) -> str:
    """Sender block, recipient, date and Betreff — assembled from data, never from the model.

    A German Bewerbung is expected to carry all four; letting the model write them would put a
    hallucinated address or date on the document, so they are built here and prepended verbatim.
    """
    german = any(marker in letter_body for marker in GERMAN_MARKERS)
    sender = [personal.full_name]
    if personal.location:
        sender.append(personal.location)
    contact = " · ".join(part for part in (personal.phone, personal.email) if part)
    if contact:
        sender.append(contact)

    recipient = [analysis.company_name]
    if analysis.location:
        recipient.append(analysis.location)

    subject = (
        f"Bewerbung als {analysis.job_title}" if german else f"Application for {analysis.job_title}"
    )
    # Emitted as HTML, not Markdown: each block needs its own DIN 5008 spacing, and a class
    # is the only way to tell the four of them apart once Markdown has flattened them to <p>.
    blocks = [
        _block("letter-sender", sender),
        _block("letter-recipient", recipient),
        _block("letter-date", [_date_line(personal, today, german=german)]),
        _block("letter-subject", [subject]),
    ]
    return "\n\n".join(blocks) + "\n\n"


def _block(class_name: str, lines: list[str]) -> str:
    body = "<br>".join(escape(line, quote=False) for line in lines)
    return f'<p class="{class_name}">{body}</p>'


def _date_line(personal: PersonalInfo, today: date, *, german: bool) -> str:
    if not german:
        return f"{today.day} {today.strftime('%B')} {today.year}"
    formatted = f"{today.day}. {GERMAN_MONTHS[today.month - 1]} {today.year}"
    city = _sender_city(personal.location)
    return f"{city}, {formatted}" if city else formatted


def _sender_city(location: str | None) -> str | None:
    if not location:
        return None
    return POSTCODE.sub("", location.split(",")[-1].strip()) or None


def build_letter_prompt(
    analysis: JobAnalysis, profile: Profile, language: str | None = None
) -> tuple[str, str]:
    system_prompt = LETTER_PROMPT_PATH.read_text(encoding="utf-8")
    language_instruction = (
        f"Write the cover letter in {language}."
        if language
        else "Write the cover letter in the same language as the job analysis below."
    )
    user_message = "\n\n".join(
        [
            language_instruction,
            "## Candidate contact details\n" + profile.personal.as_contact_lines(),
            "## Cover letter template (tone, structure, signature)\n" + profile.cover_letter_template,
            "## Candidate master CV (real experience to draw on)\n" + profile.master_cv_markdown,
            "## Job analysis\n" + json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
        ]
    )
    return system_prompt, user_message
