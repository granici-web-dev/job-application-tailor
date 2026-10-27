"""Keeping the tailored CV within two A4 pages, without asking the model again.

The limit is in the prompt, and the model reads it as advice: runs came out at three pages,
and asking again with the page count in hand never brought one down. So the pipeline
measures the rendered PDF and shortens here, in a fixed order: first the skill groups the
posting has no use for, then the layout, within floors that keep the page readable. The
experience and the projects are never cut: every role keeps every bullet, and every project
that passed the tag filter stays. A CV that still runs past two pages is a longer CV by
design: the last section that does not fit on its page starts a new one, with all after it,
instead of a few lines of it trailing onto the next page.
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
# Skill groups naming nothing the posting asks for go, down to this many groups.
MIN_SKILL_GROUPS = 4

SECTION_LINE = re.compile(r"^##\s+\S")
NEW_PAGE = "{: .new-page }"


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


def with_new_page_before(cv_markdown: str, section: int) -> str:
    """The CV with its `section`-th `## ` section (from 0) starting a new page."""
    lines = cv_markdown.splitlines()
    headings = [index for index, line in enumerate(lines) if SECTION_LINE.match(line)]
    if section >= len(headings) or NEW_PAGE in lines[headings[section]]:
        return cv_markdown
    lines[headings[section]] = f"{lines[headings[section]].rstrip()} {NEW_PAGE}"
    rebuilt = "\n".join(lines)
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


def last_split_section(spans: Sequence[tuple[int, int]]) -> int | None:
    """Counting from the end, the first section laid out across two pages, or None."""
    return next((index for index in reversed(range(len(spans))) if spans[index][0] != spans[index][1]), None)


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
# Each `## ` section's first and last page, as laid out with that layout.
Locate = Callable[[str, CvLayout], Sequence[tuple[int, int]]]


@dataclass(frozen=True)
class FittedCv:
    markdown: str
    pdf: bytes
    pages: int
    layout: CvLayout


# Applied in order, each only while the CV is still over the limit.
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


def fit_to_page_limit(
    cv_markdown: str, render: Render, posting_terms: Sequence[str] = (), locate: Locate | None = None
) -> FittedCv:
    """The CV shortened without the model until it fits MAX_CV_PAGES, or as far as allowed.

    One at a time, the skill groups that name none of `posting_terms`, down to
    MIN_SKILL_GROUPS; then the layout, within its floors. Roles, bullets and projects are never
    touched. A CV that still does not fit keeps its length; with `locate`, the last section
    laid out across two pages starts a new one instead — when it then fits whole on that page
    and no page is added.
    """
    layout = DEFAULT_CV_LAYOUT
    pdf, pages = render(cv_markdown, layout)
    logger.info("CV rendered to %d pages", pages)

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

    if pages > MAX_CV_PAGES and locate is not None:
        split = last_split_section(locate(cv_markdown, layout))
        broken = cv_markdown if split is None else with_new_page_before(cv_markdown, split)
        if broken != cv_markdown:
            broken_pdf, broken_pages = render(broken, layout)
            heading = [line for line in cv_markdown.splitlines() if SECTION_LINE.match(line)][split]
            first, last = locate(broken, layout)[split]
            if broken_pages <= pages and first == last:
                logger.info("CV runs to %d pages; '%s' starts a new page", broken_pages, heading)
                cv_markdown, pdf, pages = broken, broken_pdf, broken_pages
            else:
                # A section longer than a page, or a break that adds one, gains nothing.
                logger.info("CV runs to %d pages; a break before '%s' would not keep it whole, so none", pages, heading)
    logger.info("CV layout: %s", layout.describe())
    return FittedCv(markdown=cv_markdown, pdf=pdf, pages=pages, layout=layout)
