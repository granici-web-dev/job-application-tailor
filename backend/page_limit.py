"""Keeping the tailored CV within two A4 pages, without asking the model again.

The limit is in the prompt, and the model reads it as advice: runs came out at three pages,
and asking again with the page count in hand never brought one down. So the pipeline
measures the rendered PDF and cuts here, in a fixed order, oldest roles first.
"""

from __future__ import annotations

import re
from collections.abc import Callable

MAX_CV_PAGES = 2
# Step one: roles that started before this year keep title, employer and dates, no bullets.
EARLY_ROLE_YEAR = 2015
# Step two: roles that started before this year keep at most TRIMMED_BULLETS bullets.
OLDER_ROLE_YEAR = 2020
TRIMMED_BULLETS = 2

SECTION = re.compile(r"^##\s+\S")
ENTRY = re.compile(r"^###\s+(.*?)\s*$")
EXPERIENCE_SECTION = re.compile(
    r"^##\s*(berufserfahrung|beruflicher werdegang|werdegang|experience|employment)", re.IGNORECASE
)
DATE_LINE = re.compile(r"^\s*[_*]*\s*(\S.*?\d{4}.*?)\s*[_*]*\s*$")
YEAR = re.compile(r"\b(19|20)\d{2}\b")
BULLET = re.compile(r"^\s*[-*+]\s+")


def collapse_early_roles(cv_markdown: str) -> tuple[str, list[str]]:
    """Put each role that started before EARLY_ROLE_YEAR on one line, without its bullets.

    Title, employer and dates stay — the role is still on the CV, so the history keeps no
    gap — and only the description goes. Returns the CV and the headings it changed.
    """

    def collapse(heading: str, dates: str, body: list[str]) -> list[str] | None:
        if not any(BULLET.match(line) for line in body):
            return None
        return [f"### {heading} ({dates})", ""]

    return _rewrite_roles(cv_markdown, EARLY_ROLE_YEAR, collapse)


def trim_older_roles(cv_markdown: str) -> tuple[str, list[str]]:
    """Cut each role that started before OLDER_ROLE_YEAR down to TRIMMED_BULLETS bullets.

    The first bullets are the ones kept: the tailoring step has already put the ones that
    matter for the posting first.
    """

    def trim(heading: str, dates: str, body: list[str]) -> list[str] | None:
        bullets = [line for line in body if BULLET.match(line)]
        if len(bullets) <= TRIMMED_BULLETS:
            return None
        dropped = set(map(id, bullets[TRIMMED_BULLETS:]))
        return [f"### {heading}"] + [line for line in body if id(line) not in dropped]

    return _rewrite_roles(cv_markdown, OLDER_ROLE_YEAR, trim)


def _rewrite_roles(
    cv_markdown: str,
    started_before: int,
    rewrite: Callable[[str, str, list[str]], list[str] | None],
) -> tuple[str, list[str]]:
    """Apply `rewrite` to every experience entry that started before the given year.

    `rewrite` gets the heading, the date range and the body lines, and returns the entry's
    new lines, or None to leave it as it is.
    """
    lines = cv_markdown.splitlines()
    result: list[str] = []
    changed: list[str] = []
    in_experience = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if SECTION.match(line):
            in_experience = bool(EXPERIENCE_SECTION.match(line))
        entry = ENTRY.match(line) if in_experience else None
        if not entry:
            result.append(line)
            index += 1
            continue

        end = index + 1
        while end < len(lines) and not ENTRY.match(lines[end]) and not SECTION.match(lines[end]):
            end += 1
        body = lines[index + 1 : end]
        dates = next(
            (m.group(1) for m in map(DATE_LINE.match, body) if m and YEAR.search(m.group(1))), None
        )
        started = int(YEAR.search(dates).group(0)) if dates else None
        rewritten = (
            rewrite(entry.group(1), dates, body)
            if started is not None and started < started_before
            else None
        )
        if rewritten is None:
            result.extend(lines[index:end])
        else:
            result.extend(rewritten)
            changed.append(entry.group(1))
        index = end

    rebuilt = "\n".join(result)
    return (rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt), changed
