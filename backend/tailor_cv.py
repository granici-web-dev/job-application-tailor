from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path

from anthropic import Anthropic

from backend.emphasis import emphasis_section
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
LANGUAGES_HEADING = re.compile(r"^##\s*(sprachen|languages)\b", re.IGNORECASE)
SUMMARY_HEADING = re.compile(r"^##\s*(profil|kurzprofil|summary|profile)\b", re.IGNORECASE)
SEPARATOR = re.compile(r"^\s*(---+)?\s*$")
PROJECTS_HEADING = re.compile(r"^##\s*(projekte|projects)\b", re.IGNORECASE)
PROJECT_ENTRY = re.compile(r"^###\s+\S")
# The disciplines a project speaks to, on its own line under its dates: `_Tags: engineering, ai_`.
PROJECT_TAGS = re.compile(r"^\s*_Tags:\s*([^_]*)_\s*$", re.IGNORECASE)
# The sentence the cover letter tells the project in: `_Letter: Daneben habe ich …_`.
PROJECT_LETTER = re.compile(r"^\s*_Letter:\s*(.*?)_\s*$", re.IGNORECASE)
# An entry under the experience or project section, and the lines its introduction stops at.
ENTRY_HEADING = re.compile(r"^###\s+(.*?)\s*$")
ITALIC_LINE = re.compile(r"^\s*_[^_].*_\s*$")
INTRO_STOP = re.compile(r"^\s*([-*+]\s|\*\*|#|---)")
BULLET_LINE = re.compile(r"^\s*[-*+]\s+(.*?)\s*$")
BOLD_LINE = re.compile(r"^\s*\*\*(.+?)\*\*")
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

    Put in code after humanize, which would otherwise reword it.
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

    A project that speaks to another discipline is the one a reader skips. When no project
    carries the discipline's tag, the Projekte section goes altogether, so the CV shows the
    same projects as the letter: none. With `discipline` None — the letter's master, which the
    fact check reads — every project stays. The tag and letter lines go in any case: they are
    for the pipeline, not for the reader.
    """
    parsed = _projects(master_markdown)
    if parsed is None:
        return master_markdown
    (start, end), intro, projects = parsed
    lines = master_markdown.splitlines()
    relevant = _relevant(projects, discipline)
    if not relevant:
        rebuilt = lines[:start] + lines[end:]
        text = "\n".join(rebuilt)
        return text + "\n" if master_markdown.endswith("\n") else text
    body = [_drop_blank_run(list(project.lines)) for project in relevant]
    rebuilt = lines[: start + 1] + intro + [line for block in body for line in block] + lines[end:]
    text = "\n".join(rebuilt)
    return text + "\n" if master_markdown.endswith("\n") else text


def project_letter_sentence(master_markdown: str, discipline: str | None) -> str | None:
    """The letter sentence of the first project tagged for this discipline, if any.

    Same order as the CV's Projekte section, so the letter tells the project the reader also
    finds in the CV. With no project tagged for the discipline there is no sentence, and the
    template's [PROJEKT] goes: the paragraph is about the Weiterbildung alone.
    """
    parsed = _projects(master_markdown)
    if parsed is None:
        return None
    if discipline is None:
        return None
    return next((project.letter for project in _relevant(parsed[2], discipline) if project.letter), None)


def _relevant(projects: list[_Project], discipline: str | None) -> list[_Project]:
    if discipline is None:
        return projects
    return [project for project in projects if discipline in project.tags]


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


def with_master_entry_intros(cv_markdown: str, master_markdown: str) -> str:
    """Each entry's introduction replaced by the master CV's, word for word.

    The introduction is the paragraph without bullets between an entry's dates and its first
    bullet or bold subheading — CorLab's opening line, each project's. Like the summary, it is
    the candidate's own wording, so whatever the model or humanize made of it is overwritten
    here; an entry the master gives none loses any the model wrote. An entry whose heading is
    not the master's is left alone, and entry_intro_findings reports it.
    """
    master = _entry_intros(master_markdown)
    lines = cv_markdown.splitlines()
    for heading, (start, end), _ in reversed(_entry_spans(cv_markdown)):
        if _entry_key(heading) not in master:
            continue
        body = lines[start:end]
        first, last = _intro_span(body)
        intro = master[_entry_key(heading)]
        if first == last:
            replacement = ["", *intro] if intro else []
        else:
            replacement = intro
            if not intro:
                # Its blank line goes too, so no gap is left behind.
                last += 1 if last < len(body) and not body[last].strip() else 0
        lines[start:end] = body[:first] + replacement + body[last:]
    rebuilt = "\n".join(lines)
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


def entry_intro_findings(cv_markdown: str, master_markdown: str) -> list[str]:
    """Where an entry's introduction is not the master CV's, as instructions for the next attempt."""
    master = _entry_intros(master_markdown)
    findings = []
    for heading, _, intro in _entry_spans(cv_markdown):
        key = _entry_key(heading)
        if key not in master:
            findings.append(
                f"The entry '{heading}' is not headed as in the master CV. Keep each experience "
                "and project heading exactly as the master CV writes it."
            )
        elif intro != master[key]:
            expected = " ".join(line.strip() for line in master[key] if line.strip()) or "none"
            findings.append(f"The introduction of '{heading}' must be the master CV's, word for word: {expected}")
    return findings


def with_master_bullets(cv_markdown: str, master_markdown: str) -> str:
    """Each entry's bullets made the master CV's set, in number and wording.

    Per list (CorLab's lists sit under bold subheadings, matched by them): a bullet worded as
    the master's keeps its place, so the model's order within the entry stands; a master
    bullet that is missing — dropped, or reworded by the model or humanize — comes back
    after the master bullet it follows; a bullet the master does not have goes. An entry
    whose heading is not the master's is left alone; entry_intro_findings reports it.
    """
    master = {
        _entry_key(heading): _bullet_lists(master_markdown.splitlines()[start:end])
        for heading, (start, end), _ in _entry_spans(master_markdown)
    }
    lines = cv_markdown.splitlines()
    for heading, (start, end), _ in reversed(_entry_spans(cv_markdown)):
        master_lists = master.get(_entry_key(heading))
        if master_lists is None:
            continue
        body = lines[start:end]
        rebuilt = _with_master_lists(body, master_lists)
        if rebuilt != body:
            logger.info("Bullets of '%s' brought back to the master CV's", heading)
        lines[start:end] = rebuilt
    rebuilt_cv = "\n".join(lines)
    return rebuilt_cv + "\n" if cv_markdown.endswith("\n") else rebuilt_cv


@dataclass(frozen=True)
class _BulletList:
    """A run of bullets in an entry's body, under the bold line it follows (if any)."""

    key: str
    bold_line: str | None
    start: int
    end: int
    texts: list[str]


def _bullet_lists(body: list[str]) -> list[_BulletList]:
    lists = []
    bold_line = None
    index = 0
    while index < len(body):
        if BOLD_LINE.match(body[index]):
            bold_line = body[index].strip()
        if not BULLET_LINE.match(body[index]):
            index += 1
            continue
        start = index
        while index < len(body) and BULLET_LINE.match(body[index]):
            index += 1
        key = _entry_key(BOLD_LINE.match(bold_line).group(1)) if bold_line else ""
        texts = [BULLET_LINE.match(line).group(1) for line in body[start:index]]
        lists.append(_BulletList(key, bold_line, start, index, texts))
    return lists


def _with_master_lists(body: list[str], master_lists: list[_BulletList]) -> list[str]:
    master_texts = {master.key: master.texts for master in master_lists}
    body = list(body)
    for cv_list in reversed(_bullet_lists(body)):
        if cv_list.key in master_texts:
            merged = _merged(cv_list.texts, master_texts[cv_list.key])
            body[cv_list.start : cv_list.end] = [f"- {text}" for text in merged]
        else:
            # A list the master does not have goes, with the blank line after it.
            end = cv_list.end + (1 if cv_list.end < len(body) and not body[cv_list.end].strip() else 0)
            body[cv_list.start : end] = []
    # A whole list the model left out comes back, under the master's bold line, after the list
    # it follows in the master — or at the end of the entry when there is none.
    for position, master in enumerate(master_lists):
        current = _bullet_lists(body)
        if any(cv_list.key == master.key for cv_list in current):
            continue
        earlier = {other.key for other in master_lists[:position]}
        anchor = next((cv_list.end for cv_list in reversed(current) if cv_list.key in earlier), None)
        if anchor is None:
            while body and not body[-1].strip():
                body.pop()
            anchor = len(body)
        heading = [master.bold_line, ""] if master.bold_line else []
        body[anchor:anchor] = ["", *heading, *(f"- {text}" for text in master.texts)]
    return body


def _merged(texts: list[str], master: list[str]) -> list[str]:
    """The master's bullets, in the CV's order where it kept them word for word."""
    def same(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    wanted = {same(text): text for text in master}
    kept: list[str] = []
    for text in texts:
        if same(text) in wanted and wanted[same(text)] not in kept:
            kept.append(wanted[same(text)])
    for position, text in enumerate(master):
        if text in kept:
            continue
        before = [index for index, other in enumerate(kept) if other in master[:position]]
        kept.insert(before[-1] + 1 if before else 0, text)
    return kept


def _entry_intros(markdown: str) -> dict[str, list[str]]:
    return {_entry_key(heading): intro for heading, _, intro in _entry_spans(markdown)}


def _entry_spans(markdown: str) -> list[tuple[str, tuple[int, int], list[str]]]:
    """Each experience and project entry: its heading, its body's line range, its introduction."""
    lines = markdown.splitlines()
    spans = []
    for head, (start, end) in _level_two_sections(markdown):
        if not (EXPERIENCE_HEADING.match(head) or PROJECTS_HEADING.match(head)):
            continue
        entries = [index for index in range(start + 1, end) if ENTRY_HEADING.match(lines[index])]
        for position, entry in enumerate(entries):
            stop = entries[position + 1] if position + 1 < len(entries) else end
            body = lines[entry + 1 : stop]
            first, last = _intro_span(body)
            intro = [line.rstrip() for line in body[first:last]]
            spans.append((ENTRY_HEADING.match(lines[entry]).group(1), (entry + 1, stop), intro))
    return spans


def _intro_span(body: list[str]) -> tuple[int, int]:
    """Where the introduction sits in an entry's body; empty, after the dates, when it has none."""
    first = last = None
    after_dates = 0
    for index, line in enumerate(body):
        if not line.strip():
            continue
        if INTRO_STOP.match(line):
            break
        if ITALIC_LINE.match(line) and first is None:
            after_dates = index + 1
            continue
        if first is None:
            first = index
        last = index + 1
    if first is None:
        return after_dates, after_dates
    return first, last


def _entry_key(heading: str) -> str:
    """A heading compared without case, spacing, the kind of dash, or dates put after it.

    "Webdesigner — StarSoft SRL, Chisinau (06/2014 – 04/2016)" is a role cut to one line.
    """
    heading = re.sub(r"\s*\([^)]*\d{4}[^)]*\)\s*$", "", heading)
    return re.sub(r"\s+", " ", re.sub(r"[–—-]", "-", heading)).strip().casefold()


def split_off_education(cv_markdown: str) -> tuple[str, list[str] | None, str | None]:
    """The CV without its education section, that section's lines, and the heading after it.

    Like the summary, the education is the master CV's word for word — every entry, every
    bullet, in its order — so it never reaches humanize; put_back_master_education puts the
    master's back where it was.
    """
    sections = _level_two_sections(cv_markdown)
    index = next((i for i, (head, _) in enumerate(sections) if EDUCATION_HEADING.match(head)), None)
    if index is None:
        return cv_markdown, None, None
    lines = cv_markdown.splitlines()
    start, end = sections[index][1]
    following = sections[index + 1][0] if index + 1 < len(sections) else None
    rest = "\n".join(lines[:start] + lines[end:])
    return (rest + "\n" if cv_markdown.endswith("\n") else rest), lines[start:end], following


def put_back_master_education(
    cv_markdown: str, removed: list[str] | None, following: str | None, master_markdown: str
) -> str:
    """The CV with the master CV's education section, word for word, where the CV had its own.

    A CV that had none gets it before its languages section, or at the end. The heading and
    the separator after it are the CV's, as for the summary.
    """
    body = _master_education_body(master_markdown)
    if body is None:
        return cv_markdown
    lines = cv_markdown.splitlines()
    heading = removed[0] if removed else _master_education_heading(master_markdown)
    trailing: list[str] = []
    if removed:
        tail = removed[1:]
        while tail and SEPARATOR.match(tail[-1]):
            trailing.insert(0, tail.pop())
        while trailing and not trailing[0].strip():
            trailing.pop(0)
    if following is None and not removed:
        following = next((line for line in lines if LANGUAGES_HEADING.match(line)), None)
    at = next((i for i, line in enumerate(lines) if following is not None and line == following), len(lines))
    block = [heading, "", *body, "", *trailing]
    if at == len(lines) and lines and lines[-1].strip():
        block.insert(0, "")
    rebuilt = "\n".join(lines[:at] + block + lines[at:])
    return rebuilt + "\n" if cv_markdown.endswith("\n") or at == len(lines) else rebuilt


def education_findings(cv_markdown: str, master_markdown: str) -> list[str]:
    """Where the CV's education section is not the master CV's, word for word."""
    expected = _master_education_body(master_markdown)
    if expected is None:
        return []
    _, removed, _ = split_off_education(cv_markdown)
    if removed is None:
        return ["The CV has no education section; it carries the master CV's, word for word."]
    if _trimmed(removed[1:]) != expected:
        return ["The education section must be the master CV's, word for word: every entry and bullet, in its order."]
    return []


def _master_education_body(master_markdown: str) -> list[str] | None:
    section = next(
        (span for head, span in _level_two_sections(master_markdown) if EDUCATION_HEADING.match(head)), None
    )
    if section is None:
        return None
    start, end = section
    return _trimmed(master_markdown.splitlines()[start + 1 : end])


def _master_education_heading(master_markdown: str) -> str:
    return next(head for head, _ in _level_two_sections(master_markdown) if EDUCATION_HEADING.match(head))


def _trimmed(lines: list[str]) -> list[str]:
    """Lines without the blank lines and separators around them."""
    lines = [line.rstrip() for line in lines]
    while lines and SEPARATOR.match(lines[0]):
        lines.pop(0)
    while lines and SEPARATOR.match(lines[-1]):
        lines.pop()
    return lines


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
            *emphasis_section(analysis.discipline, kind="cv"),
        ]
    )
    return system_prompt, user_message
