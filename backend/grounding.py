"""Deterministic checks that a tailored CV carries the right skills — no more, no fewer.

The humanize guard only compares a document against its own previous version, so it cannot
see a skill that the tailoring step imported straight from the job posting. This module
closes that gap for the skills section, where such imports actually land, and the opposite
gap with it: a skill the posting asks for and the candidate really has, dropped on the way.
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
# rather than staying glued to the one before them. The pipe and the bullet are here because
# the model reaches for them to lay a group out on one line; missing one glues two real
# skills into a phrase the master CV cannot possibly contain.
ITEM_SEPARATORS = re.compile(r"[,/;·•|]|[()]")
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


def missing_required_skills(
    cv_markdown: str, master_markdown: str, required: list[str]
) -> list[str]:
    """Skills the posting asks for that the master CV backs but the tailored CV never mentions.

    Checked against the whole document, not just the skills section: a skill earns its keep
    just as well from an experience bullet, and demanding the section carry it would push the
    model to pad the list.
    """
    master_spaced = _normalize(master_markdown)
    master_squashed = master_spaced.replace(" ", "")
    cv_spaced = _normalize(cv_markdown)
    cv_squashed = cv_spaced.replace(" ", "")
    missing: list[str] = []
    for skill in required:
        # A skill the master CV does not back is not missing, it is off limits.
        if not _is_supported(skill, master_spaced, master_squashed):
            continue
        if _is_supported(skill, cv_spaced, cv_squashed) or skill in missing:
            continue
        missing.append(skill)
    return missing


# A group's line: `- **Frontend:** HTML, CSS` or `**Frontend**: HTML, CSS`.
GROUP_LINE = re.compile(r"^\s*(?:[-*+]\s+)?\*\*([^*]+?)\s*:?\s*\*\*\s*:?\s*(.*)$")


def skill_group_findings(cv_markdown: str, master_markdown: str) -> list[str]:
    """Where the CV's skill groups depart from the master CV's, as instructions for a retry.

    The groups may be reordered, thinned or left out, but each keeps the master CV's label
    word for word and holds only skills the master CV files under it. A renamed group reads
    as a claim of its own ("AI-gestützte Entwicklung" is not "AI-Entwicklung"), and a merged
    one hides which skills came from where.
    """
    master_groups = _skill_groups(master_markdown)
    if not master_groups:
        return []
    labels = ", ".join(f"'{label}'" for label in master_groups)
    findings: list[str] = []
    seen: list[str] = []
    for line in _skills_section_lines(cv_markdown):
        match = GROUP_LINE.match(line)
        if not match:
            findings.append(f"The skills line '{line.strip()}' has no group label. Use the master CV's: {labels}.")
            continue
        label, body = match.group(1).strip(), match.group(2)
        if label not in master_groups:
            findings.append(
                f"The skill group '{label}' is not one of the master CV's. Keep its labels word for word, "
                f"never rename or merge them: {labels}."
            )
            continue
        if label in seen:
            findings.append(f"The skill group '{label}' appears twice.")
        seen.append(label)
        for item in _items(body):
            # A skill no group holds is unsupported_skills' finding, not a misfiled one.
            homes = [other for other, text in master_groups.items() if _holds(text, item)]
            if homes and label not in homes:
                findings.append(
                    f"'{item}' is under the skill group '{label}', but the master CV lists it under '{homes[0]}'."
                )
    return findings


def with_master_skill_groups(cv_markdown: str, master_markdown: str) -> str:
    """The CV with its skills section replaced by the master CV's groups as they stand."""
    master_lines = _skills_section_lines(master_markdown)
    lines = cv_markdown.splitlines()
    start = next((index for index, line in enumerate(lines) if SKILL_HEADING.match(line)), None)
    if start is None or not master_lines:
        return cv_markdown
    end = next((index for index in range(start + 1, len(lines)) if HEADING.match(lines[index])), len(lines))
    # A closing rule before the next section belongs to the layout, not to the skills.
    closing = [line for line in lines[start + 1 : end] if line.strip().startswith("---")][-1:]
    rebuilt = lines[: start + 1] + ["", *master_lines, ""] + (closing + [""] if closing else []) + lines[end:]
    text = "\n".join(rebuilt)
    return text + "\n" if cv_markdown.endswith("\n") else text


def _skill_groups(cv_markdown: str) -> dict[str, str]:
    groups: dict[str, str] = {}
    for line in _skills_section_lines(cv_markdown):
        match = GROUP_LINE.match(line)
        if match:
            groups[match.group(1).strip()] = match.group(2)
    return groups


def _holds(text: str, item: str) -> bool:
    spaced = _normalize(text)
    return _is_supported(item, spaced, spaced.replace(" ", ""))


def _items(body: str) -> list[str]:
    items = []
    for raw in ITEM_SEPARATORS.split(body):
        item = raw.replace("*", "").strip(" .()")
        if item and len(item.split()) <= MAX_ITEM_WORDS:
            items.append(item)
    return items


def skill_wording(cv_markdown: str) -> list[str]:
    """The skills section's lines as plain text, category labels and parentheses kept.

    Kept whole rather than split into items: "Accessibility (WCAG 2.2 AA)" is the wording to
    reuse, and splitting would hand back "Accessibility" and "WCAG 2.2 AA" apart.
    """
    return [LIST_MARKER.sub("", line).replace("**", "").strip() for line in _skills_section_lines(cv_markdown)]


def _skill_items(cv_markdown: str) -> list[str]:
    items: list[str] = []
    for line in _skills_section_lines(cv_markdown):
        items.extend(_items(CATEGORY_LABEL.sub("", LIST_MARKER.sub("", line))))
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
