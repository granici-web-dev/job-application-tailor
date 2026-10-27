"""Keeping the tailored CV within two A4 pages, without asking the model again.

The limit is in the prompt, and the model reads it as advice: runs came out at three pages,
and asking again with the page count in hand never brought one down. So the pipeline
measures the rendered PDF and shortens here, in a fixed order: first the content, oldest
roles first, then the skill groups the posting has no use for, then the layout, within floors
that keep the page readable.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from backend.grounding import GROUP_LINE, SKILL_HEADING, _items
from backend.render_pdf import DEFAULT_CV_LAYOUT, CvLayout

logger = logging.getLogger(__name__)

MAX_CV_PAGES = 2
MIN_MARGIN_MM = 15
MIN_FONT_PT = 10
FONT_STEP_PT = 0.5
# Step one: roles that started before this year keep title, employer and dates, no bullets.
EARLY_ROLE_YEAR = 2015
# Step two: roles that started before this year keep at most TRIMMED_BULLETS bullets.
OLDER_ROLE_YEAR = 2020
TRIMMED_BULLETS = 2
# Step three: skill groups naming nothing the posting asks for go, down to this many groups.
MIN_SKILL_GROUPS = 4

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


def drop_irrelevant_skill_group(cv_markdown: str, posting_terms: Sequence[str]) -> tuple[str, list[str]]:
    """Take out the last skill group that names none of the posting's terms.

    The last one first: the tailoring step has ordered the groups by relevance. Matching
    ignores case and runs both ways, so "REST API" in a group answers a posting's "REST
    APIs", and "React" answers "React". At MIN_SKILL_GROUPS groups nothing more goes.
    Returns the CV and the label it dropped, if any.
    """
    lines = cv_markdown.splitlines()
    groups: list[tuple[int, str, str]] = []
    inside = False
    for index, line in enumerate(lines):
        if line.startswith("#"):
            inside = bool(SKILL_HEADING.match(line))
            continue
        match = GROUP_LINE.match(line) if inside else None
        if match:
            groups.append((index, match.group(1).strip(), match.group(2)))
    if len(groups) <= MIN_SKILL_GROUPS:
        return cv_markdown, []

    for index, label, body in reversed(groups):
        if _names_posting_term(body, posting_terms):
            continue
        # The blank line after a group goes with it, so no gap is left behind.
        end = index + 1
        if end < len(lines) and not lines[end].strip() and (index == 0 or not lines[index - 1].strip()):
            end += 1
        rebuilt = "\n".join(lines[:index] + lines[end:])
        return (rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt), [label]
    return cv_markdown, []


def _names_posting_term(body: str, posting_terms: Sequence[str]) -> bool:
    # Bound at the start only, so an ending ("APIs", "Designsystemen") still matches.
    def within(needle: str, haystack: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(needle)}", haystack, re.IGNORECASE) is not None

    items = _items(body)
    return any(
        within(term, body) or any(within(item, term) for item in items)
        for term in posting_terms
        if term.strip()
    )


Render = Callable[[str, CvLayout], tuple[bytes, int]]


@dataclass(frozen=True)
class FittedCv:
    markdown: str
    pdf: bytes
    pages: int
    layout: CvLayout


# Applied in order, each only while the CV is still over the limit.
_CONTENT_STEPS = (
    ("collapsed to one line", collapse_early_roles),
    ("trimmed to two bullets", trim_older_roles),
)
_LAYOUT_STEPS = (
    ("tighter spacing", lambda layout: replace(layout, compact_spacing=True)),
    (
        f"margins down to {MIN_MARGIN_MM} mm",
        lambda layout: replace(layout, margin_vertical_mm=MIN_MARGIN_MM, margin_horizontal_mm=MIN_MARGIN_MM),
    ),
    (
        f"body font down to at least {MIN_FONT_PT} pt",
        lambda layout: replace(layout, font_pt=max(MIN_FONT_PT, layout.font_pt - FONT_STEP_PT)),
    ),
)


def fit_to_page_limit(cv_markdown: str, render: Render, posting_terms: Sequence[str] = ()) -> FittedCv:
    """The CV shortened without the model until it fits MAX_CV_PAGES, or as far as allowed.

    Content first — only the oldest roles' bullets go, never a title or a date, so what is
    left has already passed the fact check — then, one at a time, the skill groups that name
    none of `posting_terms`, then the layout, within its floors. A CV that still does not
    fit goes out as it is, with a warning: a third page is better than a stopped application.
    """
    layout = DEFAULT_CV_LAYOUT
    pdf, pages = render(cv_markdown, layout)
    logger.info("CV rendered to %d pages", pages)

    for description, shorten in _CONTENT_STEPS:
        if pages <= MAX_CV_PAGES:
            break
        shorter, changed = shorten(cv_markdown)
        if not changed:
            continue
        pdf, shorter_pages = render(shorter, layout)
        logger.warning(
            "CV was %d pages; %s: %s -> %d pages", pages, description, "; ".join(changed), shorter_pages
        )
        cv_markdown, pages = shorter, shorter_pages

    while pages > MAX_CV_PAGES:
        shorter, dropped = drop_irrelevant_skill_group(cv_markdown, posting_terms)
        if not dropped:
            break
        pdf, shorter_pages = render(shorter, layout)
        logger.warning("CV was %d pages; dropped skill group: %s -> %d pages", pages, dropped[0], shorter_pages)
        cv_markdown, pages = shorter, shorter_pages

    for description, adjust in _LAYOUT_STEPS:
        if pages <= MAX_CV_PAGES:
            break
        adjusted = adjust(layout)
        if adjusted == layout:
            logger.warning("CV was %d pages; %s: already at the floor, nothing to change", pages, description)
            continue
        pdf, adjusted_pages = render(cv_markdown, adjusted)
        logger.warning("CV was %d pages; %s -> %d pages", pages, description, adjusted_pages)
        layout, pages = adjusted, adjusted_pages

    if pages > MAX_CV_PAGES:
        logger.warning("CV is still %d pages after every shortening step; it goes out as it is", pages)
    logger.info("CV layout: %s", layout.describe())
    return FittedCv(markdown=cv_markdown, pdf=pdf, pages=pages, layout=layout)
