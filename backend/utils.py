from __future__ import annotations

import re
from pathlib import Path

ILLEGAL_PATH_CHARS = re.compile(r'[/\\:*?"<>|]')
WHITESPACE = re.compile(r"\s+")
REPEATED_UNDERSCORE = re.compile(r"_+")


def sanitize_path_component(name: str) -> str:
    cleaned = ILLEGAL_PATH_CHARS.sub("", name)
    cleaned = WHITESPACE.sub("_", cleaned.strip())
    cleaned = REPEATED_UNDERSCORE.sub("_", cleaned).strip("_.")
    return cleaned or "unknown"


def cv_filename(full_name: str, company_name: str) -> str:
    return f"CV_{sanitize_path_component(full_name)}_{sanitize_path_component(company_name)}.pdf"


def cover_letter_filename(full_name: str, company_name: str) -> str:
    return f"CoverLetter_{sanitize_path_component(full_name)}_{sanitize_path_component(company_name)}.pdf"


def resolve_unique_company_dir(output_root: Path, company_name: str) -> Path:
    base = sanitize_path_component(company_name)
    candidate = output_root / base
    counter = 2
    while candidate.exists():
        candidate = output_root / f"{base}_{counter}"
        counter += 1
    return candidate
