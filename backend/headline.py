"""The headline under the candidate's name: two or three roles from a fixed list.

The model picks the roles for the posting; this module holds them to the list. A role outside
it ("Solution Architect", "Senior Frontend Developer") is something the candidate has never
been, and the headline is the first thing a recruiter reads. One exception: a posting whose
title contains a listed role ("Senior Frontend Developer React" contains "Frontend
Developer") puts that title first, whole, and the listed roles follow. The positions under
Berufserfahrung are never touched: they are what the contracts say.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEPARATOR = " · "
MIN_ROLES = 2
MAX_ROLES = 3


@dataclass(frozen=True)
class Role:
    """One role of the list, in the forms a German and an English CV write it."""

    german: tuple[str, ...]
    english: tuple[str, ...]

    def forms(self, language: str) -> tuple[str, ...]:
        return self.german if language == "de" else self.english


def _both(*forms: str) -> Role:
    return Role(german=forms, english=forms)


# Senior only on a design role: the master CV attaches it to design work alone.
ROLES = (
    _both("Design Engineer"),
    Role(german=("Fullstack-Entwickler",), english=("Full-Stack Developer",)),
    Role(german=("Frontend-Entwickler",), english=("Frontend Developer",)),
    _both("UI/UX Designer", "Senior UI/UX Designer"),
    _both("Product Designer"),
    _both("Business Analyst"),
    _both("Requirements Engineer"),
    _both("AI Engineer"),
    _both("AI Automation Engineer"),
)

DEFAULT_HEADLINES = {
    "engineering": ("Design Engineer", "Fullstack-Entwickler"),
    "design": ("Senior UI/UX Designer", "Design Engineer"),
    "analysis": ("Business Analyst", "UI/UX Designer", "Fullstack-Entwickler"),
    "ai": ("AI Engineer", "Fullstack-Entwickler"),
}
DEFAULT_DISCIPLINE = "engineering"

# The line under the headline naming the posting's position, word for word but for the
# gender marker: "Bewerbung als: Frontend Developer React / TypeScript".
APPLICATION_LABELS = {"de": "Bewerbung als", "en": "Application for"}
APPLICATION_LINE = re.compile(r"^\s*(?:Bewerbung als|Application for):")
GENDER_MARKER = re.compile(r"\s*\(\s*[mwfdxi](?:\s*/\s*[mwfdxi])+\s*\)", re.IGNORECASE)
SECTION_HEADING = re.compile(r"^##\s+\S")

GERMAN_SECTION = re.compile(r"^##\s*(profil|berufserfahrung|kenntnisse|ausbildung|sprachen)\b", re.I | re.M)
NAME_HEADING = re.compile(r"^#\s+\S")
HEADLINE_ONLY = re.compile(r"^\s*\*\*([^*]+)\*\*\s*$")


def cv_language(cv_markdown: str) -> str:
    """"de" when the CV uses German section headings, else "en"."""
    return "de" if GERMAN_SECTION.search(cv_markdown) else "en"


def read_headline(cv_markdown: str) -> str | None:
    """The bold line directly under the name heading, if the CV has one."""
    lines = cv_markdown.splitlines()
    heading = next((index for index, line in enumerate(lines) if NAME_HEADING.match(line)), None)
    if heading is None:
        return None
    for line in lines[heading + 1 :]:
        if not line.strip():
            continue
        match = HEADLINE_ONLY.match(line)
        return match.group(1).strip() if match else None
    return None


def position_name(job_title: str) -> str:
    """The job title without its gender marker: "Senior UX Designer (m/w/d)" is "Senior UX Designer"."""
    return re.sub(r"\s{2,}", " ", GENDER_MARKER.sub("", job_title)).strip()


def application_line(job_title: str, language: str) -> str:
    return f"{APPLICATION_LABELS.get(language, APPLICATION_LABELS['en'])}: {position_name(job_title)}"


def with_application_line(cv_markdown: str, job_title: str) -> str:
    """The CV with the application line directly under the headline, replacing any there was.

    Written in code from the analysis, so it never reaches the model or humanize.
    """
    lines = without_application_line(cv_markdown).splitlines()
    heading = next((index for index, line in enumerate(lines) if NAME_HEADING.match(line)), None)
    if heading is None:
        return cv_markdown
    anchor = heading
    following = next((index for index in range(heading + 1, len(lines)) if lines[index].strip()), None)
    if following is not None and HEADLINE_ONLY.match(lines[following]):
        anchor = following
    tail = lines[anchor + 1 :]
    while tail and not tail[0].strip():
        tail.pop(0)
    line = application_line(job_title, cv_language(cv_markdown))
    rebuilt = "\n".join(lines[: anchor + 1] + ["", line, ""] + tail)
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


def without_application_line(cv_markdown: str) -> str:
    """The CV without the application line, for the fact check: it quotes the posting."""
    lines = cv_markdown.splitlines()
    first_section = next((i for i, line in enumerate(lines) if SECTION_HEADING.match(line)), len(lines))
    found = [i for i in range(first_section) if APPLICATION_LINE.match(lines[i])]
    if not found:
        return cv_markdown
    index = found[0]
    end = index + 1
    # The blank line after it goes with it, so the header keeps one gap.
    if end < len(lines) and not lines[end].strip() and index > 0 and not lines[index - 1].strip():
        end += 1
    rebuilt = "\n".join(lines[:index] + lines[end:])
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


def application_line_findings(cv_markdown: str, job_title: str) -> list[str]:
    """Where the application line is not the analysis' position, word for word."""
    expected = application_line(job_title, cv_language(cv_markdown))
    lines = cv_markdown.splitlines()
    first_section = next((i for i, line in enumerate(lines) if SECTION_HEADING.match(line)), len(lines))
    found = [lines[i].strip() for i in range(first_section) if APPLICATION_LINE.match(lines[i])]
    if found == [expected]:
        return []
    return [f"The line under the headline must read '{expected}', exactly once; the CV has {found or 'none'}."]


def headline_findings(headline: str | None, *, job_title: str, language: str) -> list[str]:
    """Where the headline departs from the list, as instructions for the next attempt."""
    if not headline:
        return [
            "The CV has no headline under the name. Write one bold line of "
            f"{MIN_ROLES}–{MAX_ROLES} roles from the allowed list, separated by '{SEPARATOR.strip()}'."
        ]
    roles = [role.strip() for role in headline.split(SEPARATOR.strip())]
    findings: list[str] = []
    if not MIN_ROLES <= len(roles) <= MAX_ROLES:
        findings.append(f"The headline has {len(roles)} roles; it must have {MIN_ROLES} or {MAX_ROLES}.")
    title = posting_title(job_title)
    listed = roles
    if title:
        if roles[0] != title:
            findings.append(
                f"The posting's title contains a listed role, so the headline starts with the title "
                f"as it stands: '{title}'."
            )
        listed = roles[1:]
    allowed = [form for role in ROLES for form in role.forms(language)]
    for role in listed:
        if role not in allowed:
            findings.append(
                f"The headline role '{role}' is not on the allowed list for a "
                f"{'German' if language == 'de' else 'English'} CV: {', '.join(allowed)}."
            )
    if len(set(roles)) != len(roles):
        findings.append("The headline names the same role twice.")
    if title:
        contained = _posting_role(title)
        for role in listed:
            if role in contained.german + contained.english:
                findings.append(f"The headline role '{role}' repeats the role in the title '{title}'.")
    return findings


def posting_title(job_title: str) -> str | None:
    """The job title without its gender marker, when it contains a listed role; else None."""
    title = position_name(job_title)
    return title if title and _posting_role(title) else None


def headline_section(job_title: str = "") -> str:
    """The rules and the list, for the CV prompt."""
    lines = [
        "## Headline",
        f"Under the name, write one bold line of {MIN_ROLES} or {MAX_ROLES} roles separated by "
        f"'{SEPARATOR.strip()}', for example **Design Engineer{SEPARATOR}Fullstack-Entwickler**. Use only "
        "these roles, in the form for the CV's language (German / English):",
    ]
    for role in ROLES:
        german, english = " / ".join(role.german), " / ".join(role.english)
        lines.append(f"- {german}" if german == english else f"- {german} / {english}")
    title = posting_title(job_title)
    if title:
        lines.append(
            f"The posting's title contains a listed role, so the headline starts with the title as "
            f"it stands, '{title}', followed by one or two listed roles closest to the posting's "
            "discipline that do not repeat the role in the title."
        )
    else:
        lines.append(
            "The roles are the listed ones closest to the posting's discipline. A role the posting "
            "names that is not on the list (Solution Architect, Scrum Master, Data Scientist) never "
            "goes in; take the closest listed one instead."
        )
    lines.append(
        "Senior goes only with UI/UX Designer, never on a development or AI role, unless the "
        "posting's own title carries it. The positions under the experience section keep the "
        "titles the master CV gives them."
    )
    return "\n".join(lines)


def default_headline(discipline: str, language: str, job_title: str = "") -> str:
    """The discipline's listed roles, after the posting's title when it contains a listed role."""
    roles = [
        _in_language(role, language)
        for role in DEFAULT_HEADLINES.get(discipline, DEFAULT_HEADLINES[DEFAULT_DISCIPLINE])
    ]
    title = posting_title(job_title)
    if title:
        contained = _posting_role(title)
        others = [role for role in roles if role not in contained.german + contained.english]
        roles = [title, *others[: MAX_ROLES - 1]]
    return SEPARATOR.join(roles)


def _in_language(form: str, language: str) -> str:
    for role in ROLES:
        if form in role.german:
            return role.forms(language)[role.german.index(form)]
    return form


def _posting_role(job_title: str) -> Role | None:
    """The listed role the posting's title names, the longest match winning."""
    title = _squashed(re.sub(r"\([^)]*\)", " ", job_title))
    matches = [
        (len(_squashed(form)), role)
        for role in ROLES
        for form in role.german + role.english
        if _squashed(form) in title
    ]
    return max(matches, key=lambda match: match[0])[1] if matches else None


def _squashed(text: str) -> str:
    """Lower case without spaces or hyphens: "Fullstack Developer" is "Full-Stack Developer"."""
    return re.sub(r"[\s-]+", "", text.casefold())
