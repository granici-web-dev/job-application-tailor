from __future__ import annotations

import json
import logging
from pathlib import Path

from anthropic import Anthropic

from backend.grounding import unsupported_skills
from backend.llm import complete
from backend.models import JobAnalysis
from backend.profile import Profile

logger = logging.getLogger(__name__)

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
    cv_markdown = complete(
        client, model=model, system=system_prompt, user=user_message, max_tokens=MAX_TOKENS
    )

    invented = unsupported_skills(cv_markdown, profile.master_cv_markdown)
    if not invented:
        return cv_markdown

    logger.warning("Tailored CV listed skills absent from the master CV: %s; retrying", ", ".join(invented))
    retried = complete(
        client,
        model=model,
        system=system_prompt,
        user=user_message + "\n\n" + _correction(invented),
        max_tokens=MAX_TOKENS,
    )
    still_invented = unsupported_skills(retried, profile.master_cv_markdown)
    if len(still_invented) >= len(invented):
        logger.warning("Retry did not reduce the unsupported skills; keeping the first CV")
        return cv_markdown
    if still_invented:
        logger.warning("Tailored CV still lists unsupported skills: %s", ", ".join(still_invented))
    return retried


def _correction(invented: list[str]) -> str:
    return (
        "## Correction\n"
        "Your previous attempt listed skills the master CV does not state: "
        + ", ".join(invented)
        + ". Remove them, or replace each with the wording the master CV actually uses. "
        "The skills section may only contain terms taken from the master CV."
    )


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
