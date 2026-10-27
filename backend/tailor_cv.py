from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path

from anthropic import Anthropic

from backend.emphasis import emphasis_section
from backend.headline import headline_section
from backend.grounding import SKILL_HEADING, missing_required_skills, unsupported_skills
from backend.llm import complete
from backend.models import JobAnalysis
from backend.profile import Profile

logger = logging.getLogger(__name__)

CV_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "tailor_cv.md"
MAX_TOKENS = 4000

NAME_HEADING = re.compile(r"^#\s+\S")
HEADLINE_ONLY = re.compile(r"^\s*\*\*[^*]+\*\*\s*$")
SECTION_HEADING = re.compile(r"^##\s+\S")
EXPERIENCE_HEADING = re.compile(
    r"^##\s*(berufserfahrung|beruflicher werdegang|werdegang|experience|employment)", re.IGNORECASE
)
EDUCATION_HEADING = re.compile(r"^##\s*(ausbildung|education)", re.IGNORECASE)
SUMMARY_HEADING = re.compile(r"^##\s*(profil|kurzprofil|summary|profile)\b", re.IGNORECASE)
SEPARATOR = re.compile(r"^\s*(---+)?\s*$")
PROJECTS_HEADING = re.compile(r"^##\s*(projekte|projects)\b", re.IGNORECASE)
PROJECT_ENTRY = re.compile(r"^###\s+\S")
# The disciplines a project speaks to, on its own line under its dates: `_Tags: engineering, ai_`.
PROJECT_TAGS = re.compile(r"^\s*_Tags:\s*([^_]*)_\s*$", re.IGNORECASE)
# The sentence the cover letter tells the project in: `_Letter: Daneben habe ich …_`.
PROJECT_LETTER = re.compile(r"^\s*_Letter:\s*(.*?)_\s*$", re.IGNORECASE)
# A variant of the summary in the master CV: `### Profil (design)` under `## Profil`.
SUMMARY_VARIANT = re.compile(r"^###\s+.*\((\w+)\)\s*$")
# Which summary variant each discipline gets; an unclassified posting gets the engineering one.
SUMMARY_VARIANT_BY_DISCIPLINE = {
    "engineering": "engineering",
    "design": "design",
    "analysis": "analysis",
    "ai": "engineering",
}
DEFAULT_SUMMARY_VARIANT = "engineering"


def tailor_cv(
    analysis: JobAnalysis,
    profile: Profile,
    *,
    client: Anthropic,
    model: str,
    language: str | None = None,
    feedback: str | None = None,
) -> str:
    """`feedback` carries what the pipeline found wrong with the previous attempt."""
    system_prompt, user_message = build_cv_prompt(analysis, profile, language)
    if feedback:
        user_message += "\n\n" + feedback
    cv_markdown = complete(
        client, model=model, system=system_prompt, user=user_message, max_tokens=MAX_TOKENS
    )

    required = analysis.hard_skills + analysis.keywords
    problems = _skill_problems(cv_markdown, profile.master_cv_markdown, required)
    if not problems:
        return cv_markdown

    logger.warning("%s; retrying", problems.describe())
    retried = complete(
        client,
        model=model,
        system=system_prompt,
        user=user_message + "\n\n" + _correction(problems),
        max_tokens=MAX_TOKENS,
    )
    retried_problems = _skill_problems(retried, profile.master_cv_markdown, required)
    if retried_problems.severity >= problems.severity:
        logger.warning("Retry did not improve the skills section; keeping the first CV")
        return cv_markdown
    if retried_problems:
        logger.warning("Tailored CV still has skill problems: %s", retried_problems.describe())
    return retried


def apply_position_headline(cv_markdown: str, headline: str) -> str:
    """Put the headline directly under the name, replacing any the CV already has.

    Put back in code after humanize, which would otherwise reword a line the headline check
    has already passed.
    """
    lines = cv_markdown.splitlines()
    heading = next((index for index, line in enumerate(lines) if NAME_HEADING.match(line)), None)
    if heading is None:
        logger.warning("Tailored CV has no name heading; leaving out the position headline")
        return cv_markdown

    tail = lines[heading + 1 :]
    while tail and not tail[0].strip():
        tail.pop(0)
    if tail and HEADLINE_ONLY.match(tail[0]):
        tail.pop(0)  # the headline already there gives way to the one passed in
    while tail and not tail[0].strip():
        tail.pop(0)

    rebuilt = "\n".join(lines[: heading + 1] + ["", f"**{headline}**", ""] + tail)
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


@dataclass(frozen=True)
class _SkillProblems:
    invented: list[str]
    missing: list[str]

    def __bool__(self) -> bool:
        return bool(self.invented or self.missing)

    @property
    def severity(self) -> tuple[int, int]:
        """Ordered so a retry can never buy fewer omissions with a new fabrication."""
        return len(self.invented), len(self.missing)

    def describe(self) -> str:
        parts = []
        if self.invented:
            parts.append("listed skills absent from the master CV: " + ", ".join(self.invented))
        if self.missing:
            parts.append(
                "dropped skills the posting asks for and the master CV backs: "
                + ", ".join(self.missing)
            )
        return "Tailored CV " + "; ".join(parts)


def _skill_problems(cv_markdown: str, master_markdown: str, required: list[str]) -> _SkillProblems:
    return _SkillProblems(
        invented=unsupported_skills(cv_markdown, master_markdown),
        missing=missing_required_skills(cv_markdown, master_markdown, required),
    )


def move_skills_after_experience(cv_markdown: str) -> str:
    """Put the skills section below the experience section.

    Enforced here rather than trusted to the prompt: the model reads the heading list as a set
    of names and lands the skills block wherever it likes, which on a CV is the difference
    between leading with a keyword dump and leading with what the candidate actually did.
    """
    sections = _level_two_sections(cv_markdown)
    skills = next((i for i, (head, _) in enumerate(sections) if SKILL_HEADING.match(head)), None)
    experience = next(
        (i for i, (head, _) in enumerate(sections) if EXPERIENCE_HEADING.match(head)), None
    )
    if skills is None or experience is None or skills > experience:
        return cv_markdown

    lines = cv_markdown.splitlines()
    preamble = lines[: sections[0][1][0]]
    blocks = [lines[start:end] for _, (start, end) in sections]
    moved = blocks.pop(skills)
    blocks.insert(experience, moved)  # experience shifted down one by the pop

    rebuilt = "\n".join(preamble + [line for block in blocks for line in block])
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


def move_education_before_experience(cv_markdown: str) -> str:
    """Put the education section above the experience section.

    For a development posting the completed retraining is the candidate's only formal
    qualification in the craft being hired for, and the experience above it belongs to the
    other track. A reader who meets twelve years of design first reads the summary's claim
    as contradicted by the document under it.

    Enforced here for the same reason the skills move is: the heading order in the prompt is
    a list of names to the model, not a sequence.
    """
    sections = _level_two_sections(cv_markdown)
    education = next(
        (i for i, (head, _) in enumerate(sections) if EDUCATION_HEADING.match(head)), None
    )
    experience = next(
        (i for i, (head, _) in enumerate(sections) if EXPERIENCE_HEADING.match(head)), None
    )
    if education is None or experience is None or education < experience:
        return cv_markdown

    lines = cv_markdown.splitlines()
    preamble = lines[: sections[0][1][0]]
    blocks = [lines[start:end] for _, (start, end) in sections]
    blocks.insert(experience, blocks.pop(education))

    rebuilt = "\n".join(preamble + [line for block in blocks for line in block])
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


@dataclass(frozen=True)
class _Project:
    tags: frozenset[str]
    # The sentence the cover letter tells this project in, from its `_Letter: …_` line.
    letter: str | None
    lines: tuple[str, ...]


def with_relevant_projects(master_markdown: str, discipline: str | None) -> str:
    """The master CV with only the projects tagged for this discipline, and no tag lines.

    Two projects do not fit on two pages next to twelve years of experience, and the one
    that speaks to another discipline is the one a reader skips. When no project carries the
    discipline's tag, or `discipline` is None, every project stays. The tag and letter lines
    go in any case: they are for the pipeline, not for the reader.
    """
    parsed = _projects(master_markdown)
    if parsed is None:
        return master_markdown
    (start, end), intro, projects = parsed
    lines = master_markdown.splitlines()
    body = [_drop_blank_run(list(project.lines)) for project in _relevant(projects, discipline)]
    rebuilt = lines[: start + 1] + intro + [line for block in body for line in block] + lines[end:]
    text = "\n".join(rebuilt)
    return text + "\n" if master_markdown.endswith("\n") else text


def project_letter_sentence(master_markdown: str, discipline: str | None) -> str | None:
    """The letter sentence of the first project the CV keeps for this discipline.

    Same selection and order as the CV's Projekte section, so the letter tells the project
    the reader also finds in the CV.
    """
    parsed = _projects(master_markdown)
    if parsed is None:
        return None
    return next((project.letter for project in _relevant(parsed[2], discipline) if project.letter), None)


def _relevant(projects: list[_Project], discipline: str | None) -> list[_Project]:
    kept = [project for project in projects if discipline and discipline in project.tags]
    return kept or projects


def _projects(master_markdown: str) -> tuple[tuple[int, int], list[str], list[_Project]] | None:
    """The Projekte section's line range, the lines before its first entry, and its entries."""
    sections = _level_two_sections(master_markdown)
    span = next(((start, end) for head, (start, end) in sections if PROJECTS_HEADING.match(head)), None)
    if span is None:
        return None
    start, end = span
    intro: list[str] = []
    projects: list[_Project] = []
    for line in master_markdown.splitlines()[start + 1 : end]:
        if PROJECT_ENTRY.match(line):
            projects.append(_Project(frozenset(), None, (line,)))
            continue
        if not projects:
            intro.append(line)
            continue
        tags, letter = PROJECT_TAGS.match(line), PROJECT_LETTER.match(line)
        current = projects[-1]
        if tags:
            current = replace(current, tags=current.tags | {tag.strip().casefold() for tag in tags.group(1).split(",")})
        elif letter:
            current = replace(current, letter=letter.group(1).strip())
        else:
            current = replace(current, lines=current.lines + (line,))
        projects[-1] = current
    return span, intro, projects


def _drop_blank_run(block: list[str]) -> list[str]:
    """The entry without the doubled blank lines its removed tag and letter lines leave behind."""
    collapsed: list[str] = []
    for line in block:
        if not line.strip() and collapsed and not collapsed[-1].strip():
            continue
        collapsed.append(line)
    return collapsed


def summary_variant(discipline: str) -> str:
    return SUMMARY_VARIANT_BY_DISCIPLINE.get(discipline, DEFAULT_SUMMARY_VARIANT)


def with_summary_variant(master_markdown: str, discipline: str) -> str:
    """The master CV with its summary section reduced to the one variant this posting gets.

    Everything downstream — the tailoring prompts, the fact check, the summary put back word
    for word — reads this version, so none of it ever sees the other variants or their
    headings. A master CV without variants comes back unchanged.
    """
    sections = _level_two_sections(master_markdown)
    summary = next(((start, end) for head, (start, end) in sections if SUMMARY_HEADING.match(head)), None)
    if summary is None:
        return master_markdown
    lines = master_markdown.splitlines()
    start, end = summary
    variants: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lines[start + 1 : end]:
        match = SUMMARY_VARIANT.match(line)
        if match:
            current = variants.setdefault(match.group(1).casefold(), [])
        elif current is not None:
            current.append(line)
    if not variants:
        return master_markdown

    wanted = summary_variant(discipline)
    body = variants.get(wanted)
    if body is None:
        logger.warning("The master CV has no '%s' summary variant; using the first one", wanted)
        body = next(iter(variants.values()))
    while body and not body[0].strip():
        body = body[1:]
    while body and not body[-1].strip():
        body = body[:-1]
    rebuilt = "\n".join(lines[: start + 1] + ["", *body, ""] + lines[end:])
    return rebuilt + "\n" if master_markdown.endswith("\n") else rebuilt


def split_off_summary(cv_markdown: str) -> tuple[str, list[str] | None]:
    """The CV without its summary section, and that section's lines (None if it has none).

    The summary is not the model's to write: it is the candidate's own paragraph from the
    master CV, so it is taken out before humanize and put back afterwards by
    put_back_master_summary.
    """
    sections = _level_two_sections(cv_markdown)
    summary = next((i for i, (head, _) in enumerate(sections) if SUMMARY_HEADING.match(head)), None)
    if summary is None:
        return cv_markdown, None
    lines = cv_markdown.splitlines()
    start, end = sections[summary][1]
    rest = "\n".join(lines[:start] + lines[end:])
    return (rest + "\n" if cv_markdown.endswith("\n") else rest), lines[start:end]


def put_back_master_summary(
    cv_markdown: str, removed: list[str] | None, master_markdown: str
) -> str:
    """The CV with the master CV's summary paragraph, word for word, as its first section.

    The heading and the separator after it are the ones the tailored CV used, so the section
    reads in the CV's language and keeps its rule; only the paragraph is the master's.
    """
    master_lines = master_markdown.splitlines()
    master_sections = _level_two_sections(master_markdown)
    master_summary = next(
        ((start, end) for head, (start, end) in master_sections if SUMMARY_HEADING.match(head)), None
    )
    if master_summary is None:
        logger.warning("The master CV has no summary section; the CV goes out without one")
        return cv_markdown
    start, end = master_summary
    body = master_lines[start + 1 : end]
    while body and SEPARATOR.match(body[0]):
        body.pop(0)
    while body and SEPARATOR.match(body[-1]):
        body.pop()

    heading = removed[0] if removed else master_lines[start]
    trailing: list[str] = []
    if removed:
        tail = removed[1:]
        while tail and SEPARATOR.match(tail[-1]):
            trailing.insert(0, tail.pop())
        while trailing and not trailing[0].strip():
            trailing.pop(0)
    block = [heading, "", *body, "", *trailing]

    lines = cv_markdown.splitlines()
    first = next((i for i, line in enumerate(lines) if SECTION_HEADING.match(line)), len(lines))
    rebuilt = "\n".join(lines[:first] + block + lines[first:])
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


def _level_two_sections(cv_markdown: str) -> list[tuple[str, tuple[int, int]]]:
    """Each `## ` heading with the line range of the block it owns, up to the next `## `."""
    lines = cv_markdown.splitlines()
    starts = [index for index, line in enumerate(lines) if SECTION_HEADING.match(line)]
    return [
        (lines[start], (start, starts[position + 1] if position + 1 < len(starts) else len(lines)))
        for position, start in enumerate(starts)
    ]


def _correction(problems: _SkillProblems) -> str:
    lines = ["## Correction"]
    if problems.invented:
        lines.append(
            "Your previous attempt listed skills the master CV does not state: "
            + ", ".join(problems.invented)
            + ". Remove them, or replace each with the wording the master CV actually uses. "
            "The skills section may only contain terms taken from the master CV."
        )
    if problems.missing:
        lines.append(
            "Your previous attempt left out skills this posting asks for even though the master "
            "CV backs them: "
            + ", ".join(problems.missing)
            + ". Add each one, in the master CV's own wording, and put them where the posting's "
            "requirements are answered first."
        )
    return "\n".join(lines)


def build_cv_prompt(
    analysis: JobAnalysis, profile: Profile, language: str | None = None
) -> tuple[str, str]:
    system_prompt = CV_PROMPT_PATH.read_text(encoding="utf-8")
    language_instruction = (
        f"Write the CV in {language}."
        if language
        else "Write the CV in the same language as the job analysis below."
    )
    user_message = "\n\n".join(
        [
            language_instruction,
            "## Candidate contact details\n" + profile.personal.as_contact_lines(),
            "## Candidate master CV\n" + profile.master_cv_markdown,
            "## Job analysis\n" + json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
            headline_section(),
            *emphasis_section(analysis.discipline, kind="cv"),
        ]
    )
    return system_prompt, user_message
