from __future__ import annotations

import logging
import re
from pathlib import Path

from anthropic import Anthropic

from backend.llm import complete

logger = logging.getLogger(__name__)

HUMANIZE_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "humanize.md"
MAX_TOKENS = {"cover_letter": 1500, "cv": 4000}
KIND_DIRECTIVES = {
    "cover_letter": "This document is a COVER LETTER. Apply the cover-letter rules in full.",
    "cv": (
        "This document is a CV. Apply only the CV rules: rephrase wording at the sentence level, "
        "and never change the structure, the section headings, the bullet points, or the bold."
    ),
}

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
URL = re.compile(r"https?://\S+")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*%?")
WORD = re.compile(r"\w+", re.UNICODE)
INTERNAL_CAPITAL = re.compile(r"[a-zäöü][A-ZÄÖÜ]")


def humanize(text: str, *, kind: str, client: Anthropic, model: str) -> str:
    system_prompt = build_humanize_prompt(kind)
    candidate = complete(client, model=model, system=system_prompt, user=text, max_tokens=MAX_TOKENS[kind])

    if not facts_preserved(text, candidate):
        logger.warning("humanize changed factual tokens; keeping the tailored %s", kind)
        return text
    if kind == "cv" and _markdown_headings(text) != _markdown_headings(candidate):
        logger.warning("humanize changed CV section headings; keeping the tailored CV")
        return text
    return candidate


def build_humanize_prompt(kind: str) -> str:
    base = HUMANIZE_PROMPT_PATH.read_text(encoding="utf-8")
    return f"{base}\n\n{KIND_DIRECTIVES[kind]}"


def facts_preserved(before: str, after: str) -> bool:
    return extract_factual_tokens(before) == extract_factual_tokens(after)


def extract_factual_tokens(text: str) -> set[str]:
    tokens = set(EMAIL.findall(text))
    tokens.update(URL.findall(text))
    tokens.update(NUMBER.findall(text))
    tokens.update(word for word in WORD.findall(text) if _is_significant(word))
    return tokens


def _is_significant(word: str) -> bool:
    return (
        any(character.isdigit() for character in word)
        or bool(INTERNAL_CAPITAL.search(word))
        or (len(word) >= 2 and word.isupper())
    )


def _markdown_headings(markdown_text: str) -> list[str]:
    return [line.strip() for line in markdown_text.splitlines() if line.lstrip().startswith("#")]
