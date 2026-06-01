from __future__ import annotations

import json
from pathlib import Path

from anthropic import Anthropic

from backend.llm import complete
from backend.models import JobAnalysis
from backend.profile import Profile

CV_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "tailor_cv.md"
MAX_TOKENS = 4000


def tailor_cv(
    analysis: JobAnalysis,
    profile: Profile,
    *,
    client: Anthropic,
    model: str,
    language: str | None = None,
) -> str:
    system_prompt, user_message = build_cv_prompt(analysis, profile, language)
    return complete(client, model=model, system=system_prompt, user=user_message, max_tokens=MAX_TOKENS)


def build_cv_prompt(
    analysis: JobAnalysis, profile: Profile, language: str | None = None
) -> tuple[str, str]:
    system_prompt = CV_PROMPT_PATH.read_text(encoding="utf-8")
    language_instruction = (
        f"Write the CV in {language}."
        if language
        else "Write the CV in the same language as the job analysis below."
    )
    user_message = "\n\n".join(
        [
            language_instruction,
            "## Candidate contact details\n" + profile.personal.as_contact_lines(),
            "## Candidate master CV\n" + profile.master_cv_markdown,
            "## Job analysis\n" + json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
        ]
    )
    return system_prompt, user_message
