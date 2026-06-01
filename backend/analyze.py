from __future__ import annotations

import json
from pathlib import Path

from anthropic import Anthropic

from backend.errors import JobAnalysisError
from backend.llm import complete
from backend.models import JobAnalysis

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "analyze.md"
MAX_TOKENS = 2000
ANALYSIS_ATTEMPTS = 2


def analyze_job(job_text: str, *, client: Anthropic, model: str) -> JobAnalysis:
    system_prompt = _load_system_prompt()
    for attempt in range(ANALYSIS_ATTEMPTS):
        raw = complete(client, model=model, system=system_prompt, user=job_text, max_tokens=MAX_TOKENS)
        try:
            data = json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            if attempt + 1 == ANALYSIS_ATTEMPTS:
                raise JobAnalysisError(
                    "The model did not return valid JSON for the job analysis after two attempts. "
                    "Try running the command again."
                )
            continue
        return JobAnalysis.from_response_dict(data)


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")
