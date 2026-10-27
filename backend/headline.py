"""The headline under the candidate's name: two or three roles from a fixed list.

The model picks the roles for the posting; this module holds them to the list. A role outside
it ("Solution Architect", "Senior Frontend Developer") is something the candidate has never
been, and the headline is the first thing a recruiter reads. The positions under
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
}
DEFAULT_DISCIPLINE = "engineering"

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
    allowed = [form for role in ROLES for form in role.forms(language)]
    for role in roles:
        if role not in allowed:
            findings.append(
                f"The headline role '{role}' is not on the allowed list for a "
                f"{'German' if language == 'de' else 'English'} CV: {', '.join(allowed)}."
            )
    if len(set(roles)) != len(roles):
        findings.append("The headline names the same role twice.")
    posting_role = _posting_role(job_title)
    if posting_role and roles and roles[0] not in posting_role.forms(language):
        findings.append(
            f"The posting's role is on the allowed list, so the headline starts with "
            f"'{posting_role.forms(language)[0]}'."
        )
    return findings


def headline_section() -> str:
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
    lines += [
        "When the posting's own role is on this list, it comes first. The others are the listed "
        "roles closest to the posting's discipline. A role the posting names that is not on the "
        "list (Solution Architect, Scrum Master, Data Scientist) never goes in; take the closest "
        "listed one instead. Senior goes only with UI/UX Designer, never on a development or AI "
        "role. The positions under the experience section keep the titles the master CV gives them.",
    ]
    return "\n".join(lines)


def default_headline(discipline: str, language: str) -> str:
    roles = DEFAULT_HEADLINES.get(discipline, DEFAULT_HEADLINES[DEFAULT_DISCIPLINE])
    return SEPARATOR.join(_in_language(role, language) for role in roles)


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
