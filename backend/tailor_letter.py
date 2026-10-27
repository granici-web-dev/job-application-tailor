from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from anthropic import Anthropic

from backend.analyze import _strip_json_fences
from backend.errors import LLMError, ProfileError
from backend.grounding import skill_wording
from backend.llm import complete
from backend.models import JobAnalysis
from backend.profile import PersonalInfo, Profile

LETTER_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "tailor_letter.md"
MAX_TOKENS = 1500
MAX_LETTER_WORDS = 300
# At most this many sentences of the adjustable paragraph may differ from the template.
MAX_CHANGED_SENTENCES = 1
MAX_CHANGED_SENTENCE_WORDS = 30
# A dash between spaces sets off an insertion; a hyphen inside a compound ("WCAG-Audit") does not.
INSERTION_DASH = re.compile(r"\s[–—-]\s")

GERMAN_MONTHS = (
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)
GERMAN_MARKERS = ("Sehr geehrte", "Mit freundlichen Grüßen", "Guten Tag")
POSTCODE = re.compile(r"^\d{4,6}\s+")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
PLACEHOLDER = re.compile(r"\[[A-ZÄÖÜ][^\]]*\]")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")
# A word that presumes a vacancy, also as the head of a compound ("Stellenanzeige").
VACANCY_WORD = re.compile(r"(?<!\w)(?:stelle|ausschreibung|position)\w*", re.IGNORECASE)


@dataclass(frozen=True)
class LetterTemplate:
    """The cover letter template, read as the paragraphs the letter is assembled from.

    The order is fixed: a salutation placeholder, the opening paragraph the model rewrites
    for the posting, the paragraph it may adjust by one sentence, the paragraphs that go in
    word for word, and the signature.
    """

    intro: str
    adjustable: str
    fixed: tuple[str, ...]
    signature: str


def parse_letter_template(template_text: str) -> LetterTemplate:
    text = HTML_COMMENT.sub("", template_text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) < 5:
        raise ProfileError(
            "The cover letter template needs at least five paragraphs: salutation, opening, the "
            "paragraph about the current position, at least one more paragraph, and the signature."
        )
    return LetterTemplate(
        intro=paragraphs[1],
        adjustable=paragraphs[2],
        fixed=tuple(paragraphs[3:-1]),
        signature=paragraphs[-1],
    )


def fill_placeholders(text: str, analysis: JobAnalysis) -> str:
    for placeholder, value in (
        ("[POSITION]", analysis.job_title),
        ("[UNTERNEHMEN]", analysis.company_name),
        ("[COMPANY]", analysis.company_name),
    ):
        text = text.replace(placeholder, value)
    return text


def with_project_sentence(template_text: str, sentence: str | None) -> str:
    """The template with [PROJEKT] replaced by the project sentence chosen for this posting.

    Filled before the template is read, so the sentence is one more word-for-word part of a
    fixed paragraph, checked like the rest. Without a sentence the placeholder goes.
    """
    if sentence:
        return template_text.replace("[PROJEKT]", sentence)
    return re.sub(r"\s*\[PROJEKT\]", "", template_text)


def tailor_letter(
    analysis: JobAnalysis,
    profile: Profile,
    *,
    client: Anthropic,
    model: str,
    feedback: str | None = None,
    company_page: str | None = None,
) -> str:
    """The letter body, salutation to signature, assembled around the model's three parts.

    The model writes the salutation, the opening and the adjusted paragraph; every other
    paragraph comes from the template untouched. `feedback` carries what the pipeline found
    wrong with the previous attempt. `company_page` is the page's text when the application is
    unsolicited — the position entered by hand, none in the posting — and the opening then
    speaks of the company instead of a vacancy.
    """
    template = parse_letter_template(profile.cover_letter_template)
    system_prompt, user_message = build_letter_prompt(analysis, profile, template, company_page)
    if feedback:
        user_message += "\n\n" + feedback
    raw = complete(client, model=model, system=system_prompt, user=user_message, max_tokens=MAX_TOKENS)
    try:
        parts = json.loads(_strip_json_fences(raw))
        salutation, intro, adjusted = (
            parts["salutation"], parts["intro"], parts["adjusted_paragraph"]
        )
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise LLMError("The model did not return the cover letter parts in the expected form.") from error
    return assemble_letter(template, analysis, salutation=salutation, intro=intro, adjusted=adjusted)


def assemble_letter(
    template: LetterTemplate, analysis: JobAnalysis, *, salutation: str, intro: str, adjusted: str
) -> str:
    paragraphs = [
        salutation.strip(),
        intro.strip(),
        adjusted.strip(),
        *(fill_placeholders(paragraph, analysis) for paragraph in template.fixed),
        template.signature,
    ]
    return "\n\n".join(paragraphs)


def template_findings(letter: str, template: LetterTemplate, analysis: JobAnalysis) -> list[str]:
    """Where the letter body departs from the template beyond what the model may change.

    Checked in code, not trusted to the prompt: the fixed paragraphs are the candidate's own
    words, and the model rewrites a paragraph it was told to copy as readily as one it was
    told to write.
    """
    findings: list[str] = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", letter) if p.strip()]
    expected_fixed = [fill_placeholders(p, analysis) for p in template.fixed] + [template.signature]
    expected_count = 3 + len(expected_fixed)
    if len(paragraphs) != expected_count:
        return [
            f"The letter has {len(paragraphs)} paragraphs; it must have {expected_count}: the "
            "salutation, one opening paragraph, the adjusted paragraph, then the template's "
            "remaining paragraphs and signature. Write the opening as a single paragraph."
        ]

    for got, want in zip(paragraphs[3:], expected_fixed):
        if _squashed(got) != _squashed(want):
            findings.append(f"The paragraph starting '{_start(want)}' must match the template word for word.")

    template_sentences = [_squashed(s) for s in _sentences(fill_placeholders(template.adjustable, analysis))]
    adjusted_sentences = [_squashed(s) for s in _sentences(paragraphs[2])]
    added = [s for s in adjusted_sentences if s not in template_sentences]
    removed = [s for s in template_sentences if s not in adjusted_sentences]
    if max(len(added), len(removed)) > MAX_CHANGED_SENTENCES:
        findings.append(
            f"In the paragraph starting '{_start(template.adjustable)}', {max(len(added), len(removed))} "
            f"sentences differ from the template; change at most {MAX_CHANGED_SENTENCES} and copy the "
            "rest word for word."
        )

    leftover = PLACEHOLDER.findall(letter)
    if leftover:
        findings.append(f"The letter still contains template placeholders: {', '.join(leftover)}.")

    words = len(letter.split())
    if words > MAX_LETTER_WORDS:
        findings.append(
            f"The letter has {words} words; the limit is {MAX_LETTER_WORDS}. Shorten the opening "
            "paragraph, or drop the sentence you added."
        )
    return findings


def changed_sentence_findings(letter: str, template: LetterTemplate, analysis: JobAnalysis) -> list[str]:
    """Where the sentence the model changed in the adjustable paragraph is too long or interrupted.

    Kept apart from template_findings because a miss here has a safe way out: the template's
    own paragraph, which the pipeline falls back to instead of failing the letter.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", letter) if p.strip()]
    if len(paragraphs) < 3:
        return []
    template_sentences = {_squashed(s) for s in _sentences(fill_placeholders(template.adjustable, analysis))}
    findings: list[str] = []
    for sentence in _sentences(paragraphs[2]):
        if _squashed(sentence) in template_sentences:
            continue
        words = len(sentence.split())
        if words > MAX_CHANGED_SENTENCE_WORDS:
            findings.append(
                f"The sentence you changed in the paragraph starting '{_start(template.adjustable)}' "
                f"has {words} words; the limit is {MAX_CHANGED_SENTENCE_WORDS}."
            )
        if INSERTION_DASH.search(sentence):
            findings.append(
                f"The sentence you changed in the paragraph starting '{_start(template.adjustable)}' "
                "sets off an insertion with a dash. Write it without one."
            )
    return findings


def unsolicited_intro_findings(letter: str, analysis: JobAnalysis) -> list[str]:
    """Where the opening of an unsolicited application reads as an answer to a vacancy."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", letter) if p.strip()]
    if len(paragraphs) < 2:
        return []
    intro = paragraphs[1]
    opening = f"ich bewerbe mich initiativ als {analysis.job_title} bei {analysis.company_name}"
    findings: list[str] = []
    if not re.match(
        rf"ich bewerbe mich initiativ als {re.escape(analysis.job_title)} bei (?:der |dem )?"
        rf"{re.escape(analysis.company_name)}",
        intro,
    ):
        findings.append(f"The opening paragraph must begin with '{opening}'.")
    # The title and the company are the analysis' words, not the model's.
    rest = intro.replace(analysis.job_title, " ").replace(analysis.company_name, " ")
    for word in sorted({match.group(0) for match in VACANCY_WORD.finditer(rest)}):
        findings.append(
            f"The opening paragraph says '{word}'. This is an unsolicited application: there is no "
            "vacancy, so Stelle, Ausschreibung and Position never appear in it."
        )
    return findings


def company_sentence(letter: str) -> str:
    """The opening's second sentence: in an unsolicited application, what the company does."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", letter) if p.strip()]
    sentences = _sentences(paragraphs[1]) if len(paragraphs) > 1 else []
    return sentences[1] if len(sentences) > 1 else ""


def restore_template_paragraph(letter: str, template: LetterTemplate, analysis: JobAnalysis) -> str:
    """The letter with the adjustable paragraph put back exactly as the template has it."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", letter) if p.strip()]
    paragraphs[2] = fill_placeholders(template.adjustable, analysis)
    return "\n\n".join(paragraphs)


def _sentences(paragraph: str) -> list[str]:
    return [part for part in SENTENCE_END.split(paragraph.strip()) if part.strip()]


def _squashed(text: str) -> str:
    return " ".join(text.split())


def _start(paragraph: str) -> str:
    return " ".join(paragraph.split()[:6]) + " …"


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
    if analysis.contact_person:
        recipient.append(f"{'z. Hd. ' if german else 'Attn: '}{analysis.contact_person}")
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
    analysis: JobAnalysis, profile: Profile, template: LetterTemplate, company_page: str | None = None
) -> tuple[str, str]:
    system_prompt = LETTER_PROMPT_PATH.read_text(encoding="utf-8")
    fixed = [fill_placeholders(p, analysis) for p in template.fixed] + [template.signature]
    budget = MAX_LETTER_WORDS - sum(len(p.split()) for p in fixed)
    user_message = "\n\n".join(
        [
            "## Candidate contact details\n" + profile.personal.as_contact_lines(),
            "## Opening paragraph to rewrite for this posting\n" + template.intro,
            "## Paragraph you may adjust by one sentence\n" + template.adjustable,
            "## Paragraphs that follow word for word (context only, do not return them)\n"
            + "\n\n".join(fixed),
            f"## Word budget\nThe salutation, the opening and the adjusted paragraph together may "
            f"use at most {budget} words.",
            "## Terms you may use (the only wording for skills, technologies and methods in the "
            "intro and the changed sentence)\n"
            + "\n".join(f"- {line}" for line in skill_wording(profile.master_cv_markdown)),
            "## Candidate master CV (the only source of facts)\n" + profile.master_cv_markdown,
            "## Job analysis\n" + json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
            *(_unsolicited_sections(analysis, company_page) if company_page is not None else []),
        ]
    )
    return system_prompt, user_message


def _unsolicited_sections(analysis: JobAnalysis, company_page: str) -> list[str]:
    return [
        "## Unsolicited application\n"
        "The page names no position: the candidate applies on their own initiative, as "
        f"{analysis.job_title}. This overrides the rules for the intro above. Its first sentence "
        f"begins word for word with 'ich bewerbe mich initiativ als {analysis.job_title} bei "
        f"{analysis.company_name}', in lower case after the salutation's comma (an article before "
        "the company name where German needs one, 'bei der …'). Its second sentence is about the company — what it does, taken from its page "
        "below — and not about a vacancy or about the candidate; in that sentence you may use the "
        "page's own words. The words Stelle, Ausschreibung and Position never appear in the intro.",
        "## The company's page\n" + company_page,
    ]
