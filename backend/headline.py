"""The headline under the candidate's name: the posting's position, or listed roles.

Written in code, never by the model. A posting whose title contains a listed role ("Senior
Frontend Developer React" contains "Frontend Developer") gets its title as the headline, as the
posting writes it but for the gender marker. A title outside the list ("Solution Architect") is
something the candidate has never been, so the discipline's listed roles stand in for it. The
positions under Berufserfahrung are never touched: they are what the contracts say.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEPARATOR = " · "


@dataclass(frozen=True)
class Role:
    """One role of the list, in the forms a German and an English CV write it.

    `aliases` are further names a posting gives the role.
    """

    german: tuple[str, ...]
    english: tuple[str, ...]
    aliases: tuple[str, ...] = ()

    def forms(self, language: str) -> tuple[str, ...]:
        return self.german if language == "de" else self.english


def _both(*forms: str, aliases: tuple[str, ...] = ()) -> Role:
    return Role(german=forms, english=forms, aliases=aliases)


ROLES = (
    _both("Design Engineer"),
    Role(german=("Fullstack-Entwickler",), english=("Full-Stack Developer",)),
    Role(german=("Frontend-Entwickler",), english=("Frontend Developer",)),
    _both(
        "UI/UX Designer",
        "Senior UI/UX Designer",
        aliases=("UX/UI Designer", "UX Designer", "UI Designer"),
    ),
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

_GENDER = r"(?:[mwfdx]|div|divers)"
GENDER_MARKER = re.compile(
    rf"\s*\(\s*(?:{_GENDER}(?:\s*[/|,]\s*{_GENDER})+|[mwfdx]{{3}}|all genders|gn\*?)\s*\)"
    rf"|\s+{_GENDER}(?:/{_GENDER}){{2}}\b",
    re.IGNORECASE,
)
EDGE_SEPARATORS = " -–—/|,:"

GERMAN_SECTION = re.compile(r"^##\s*(profil|berufserfahrung|kenntnisse|ausbildung|sprachen)\b", re.I | re.M)


def cv_language(cv_markdown: str) -> str:
    """"de" when the CV uses German section headings, else "en"."""
    return "de" if GERMAN_SECTION.search(cv_markdown) else "en"


def position_name(job_title: str) -> str:
    """The job title without its gender marker: "Senior UX Designer (m/w/d)" is "Senior UX Designer"."""
    return _tidy(GENDER_MARKER.sub("", job_title))


def posting_title(job_title: str) -> str | None:
    """The title without its gender marker, when it contains a listed role; else None."""
    title = position_name(job_title)
    return title if _posting_role(title) else None


def cv_headline(job_title: str, discipline: str, language: str) -> str:
    """The posting's title when it contains a listed role, else the discipline's listed roles."""
    return posting_title(job_title) or default_headline(discipline, language)


def default_headline(discipline: str, language: str) -> str:
    """The discipline's listed roles, in the CV's language."""
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
        for form in role.german + role.english + role.aliases
        if _squashed(form) in title
    ]
    return max(matches, key=lambda match: match[0])[1] if matches else None


def _squashed(text: str) -> str:
    """Lower case without spaces or hyphens: "Fullstack Developer" is "Full-Stack Developer"."""
    return re.sub(r"[\s-]+", "", text.casefold())


def _tidy(text: str) -> str:
    return re.sub(r"\s{2,}", " ", text).strip(EDGE_SEPARATORS)
