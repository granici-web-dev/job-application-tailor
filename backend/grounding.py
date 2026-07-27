"""Deterministic check that a tailored CV lists no skill the master CV does not state.

The humanize guard only compares a document against its own previous version, so it cannot
see a skill that the tailoring step imported straight from the job posting. This module
closes that gap for the skills section, where such imports actually land.
"""

from __future__ import annotations

import re

SKILL_HEADING = re.compile(r"^\s*#+\s*(kenntnis|f[äa]higkeit|skill|kompetenz|technical)", re.IGNORECASE)
HEADING = re.compile(r"^\s*#")
# A category label the model invents to group the list ("**Frontend:**", "**AI Tools**"),
# with or without the colon. It is scaffolding, not a claimed skill.
CATEGORY_LABEL = re.compile(r"^\s*(?:\*\*[^*]{1,60}\*\*\s*:?|[^:*\n]{1,40}:)\s*")
LIST_MARKER = re.compile(r"^\s*[-*+]\s+")
NON_WORD = re.compile(r"[^0-9a-zà-öø-ÿ]+", re.IGNORECASE)

# Parentheses hold examples ("AI Tools (Claude Code, Codex)"), so they open a new item
# rather than staying glued to the one before them.
ITEM_SEPARATORS = re.compile(r"[,/;·()]")
MAX_ITEM_WORDS = 6


def unsupported_skills(cv_markdown: str, master_markdown: str) -> list[str]:
    """Skill entries in the tailored CV that the master CV does not back, in document order."""
    spaced = _normalize(master_markdown)
    squashed = spaced.replace(" ", "")
    unsupported: list[str] = []
    for item in _skill_items(cv_markdown):
        if not _is_supported(item, spaced, squashed) and item not in unsupported:
            unsupported.append(item)
    return unsupported


def _skill_items(cv_markdown: str) -> list[str]:
    items: list[str] = []
    for line in _skills_section_lines(cv_markdown):
        body = CATEGORY_LABEL.sub("", LIST_MARKER.sub("", line))
        for raw in ITEM_SEPARATORS.split(body):
            item = raw.replace("*", "").strip(" .()")
            if item and len(item.split()) <= MAX_ITEM_WORDS:
                items.append(item)
    return items


def _skills_section_lines(cv_markdown: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for line in cv_markdown.splitlines():
        if HEADING.match(line):
            inside = bool(SKILL_HEADING.match(line))
            continue
        if inside and line.strip() and not line.strip().startswith("---"):
            lines.append(line)
    return lines


def _is_supported(item: str, master_spaced: str, master_squashed: str) -> bool:
    normalized = _normalize(item)
    if not normalized:
        return True
    # Two passes: spaced catches ordinary phrases, squashed absorbs the difference between
    # German compounds and their hyphenated or spaced variants (Design-Systeme / Designsystemen).
    return normalized in master_spaced or normalized.replace(" ", "") in master_squashed


def _normalize(text: str) -> str:
    words = (_singularize(word) for word in NON_WORD.sub(" ", text.casefold()).split())
    return " ".join(word for word in words if word)


def _singularize(word: str) -> str:
    # Crude on purpose: it runs on both sides of the comparison, so over-stemming stays
    # symmetric and harmless. The length floor keeps CSS, AWS, and JS intact.
    for suffix in ("en", "e", "s"):
        if len(word) > 2 + len(suffix) and word.endswith(suffix):
            return word[: -len(suffix)]
    return word
