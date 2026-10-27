"""Keeping the tailored CV within two A4 pages, without asking the model again.

The limit is in the prompt, and the model reads it as advice: runs came out at three pages,
and asking again with the page count in hand never brought one down. So the pipeline
measures the rendered PDF and shortens here, in a fixed order: first the skill groups the
posting has no use for, then the layout, within floors that keep the page readable. The
experience and the projects are never cut: every role keeps every bullet, and every project
that passed the tag filter stays. A CV that still runs past two pages is a three-page CV by
design: Ausbildung and Sprachen then start on a page of their own, instead of a few lines of
them trailing onto the last one.
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

EDUCATION_SECTION = re.compile(r"^(##\s*(?:ausbildung|education)\b.*?)\s*$", re.IGNORECASE)
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


def with_education_on_new_page(cv_markdown: str) -> str:
    """The CV with its education section starting a new page; Sprachen follows it there."""
    lines = cv_markdown.splitlines()
    for index, line in enumerate(lines):
        match = EDUCATION_SECTION.match(line)
        if match and NEW_PAGE not in line:
            lines[index] = f"{match.group(1)} {NEW_PAGE}"
            break
    rebuilt = "\n".join(lines)
    return rebuilt + "\n" if cv_markdown.endswith("\n") else rebuilt


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

    One at a time, the skill groups that name none of `posting_terms`, down to
    MIN_SKILL_GROUPS; then the layout, within its floors. Roles, bullets and projects are never
    touched. A CV that still does not fit is a three-page CV, with its education section
    starting a new page.
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

    if pages > MAX_CV_PAGES:
        broken = with_education_on_new_page(cv_markdown)
        if broken != cv_markdown:
            pdf, pages = render(broken, layout)
            cv_markdown = broken
            logger.info("CV runs past %d pages; Ausbildung starts a new page -> %d pages", MAX_CV_PAGES, pages)
    logger.info("CV layout: %s", layout.describe())
    return FittedCv(markdown=cv_markdown, pdf=pdf, pages=pages, layout=layout)
