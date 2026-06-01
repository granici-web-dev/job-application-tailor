from __future__ import annotations

import json
from pathlib import Path

from anthropic import Anthropic

from backend.llm import complete
from backend.models import JobAnalysis
from backend.profile import Profile

LETTER_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "tailor_letter.md"
MAX_TOKENS = 1500


def tailor_letter(
    analysis: JobAnalysis,
    profile: Profile,
    *,
    client: Anthropic,
    model: str,
    language: str | None = None,
) -> str:
    system_prompt, user_message = build_letter_prompt(analysis, profile, language)
    return complete(client, model=model, system=system_prompt, user=user_message, max_tokens=MAX_TOKENS)


def build_letter_prompt(
    analysis: JobAnalysis, profile: Profile, language: str | None = None
) -> tuple[str, str]:
    system_prompt = LETTER_PROMPT_PATH.read_text(encoding="utf-8")
    language_instruction = (
        f"Write the cover letter in {language}."
        if language
        else "Write the cover letter in the same language as the job analysis below."
    )
    user_message = "\n\n".join(
        [
            language_instruction,
            "## Candidate contact details\n" + profile.personal.as_contact_lines(),
            "## Cover letter template (tone, structure, signature)\n" + profile.cover_letter_template,
            "## Candidate master CV (real experience to draw on)\n" + profile.master_cv_markdown,
            "## Job analysis\n" + json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
        ]
    )
    return system_prompt, user_message
