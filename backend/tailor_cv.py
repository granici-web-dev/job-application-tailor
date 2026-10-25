from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
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


def tailor_cv(
    analysis: JobAnalysis,
    profile: Profile,
    *,
    client: Anthropic,
    model: str,
    language: str | None = None,
) -> str:
    system_prompt, user_message = build_cv_prompt(analysis, profile, language)
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


def apply_position_headline(cv_markdown: str, job_title: str) -> str:
    """Put the position being applied for directly under the name.

    Taken from the job analysis rather than from the model, which otherwise writes whatever
    headline it sees fit — sometimes the posting's title, sometimes the candidate's own.
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
        tail.pop(0)  # the model wrote its own headline; the job title replaces it
    while tail and not tail[0].strip():
        tail.pop(0)

    rebuilt = "\n".join(lines[: heading + 1] + ["", f"**{job_title}**", ""] + tail)
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
