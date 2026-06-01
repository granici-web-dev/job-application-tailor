from __future__ import annotations

import os
from dataclasses import dataclass

from anthropic import Anthropic
from dotenv import load_dotenv

from backend.errors import ConfigError

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_FRONTEND_ORIGIN = "http://localhost:5173"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model: str


def load_settings() -> Settings:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file "
            "(ANTHROPIC_API_KEY=sk-ant-...) and run again."
        )
    model = os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL
    return Settings(anthropic_api_key=api_key, model=model)


def make_anthropic_client(settings: Settings) -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def frontend_origins() -> list[str]:
    load_dotenv()
    raw = os.environ.get("FRONTEND_ORIGIN", "").strip()
    if not raw:
        return [DEFAULT_FRONTEND_ORIGIN]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
