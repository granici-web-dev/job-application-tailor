from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.errors import ProfileError

MASTER_CV_FILENAME = "master_cv.md"
COVER_LETTER_TEMPLATE_FILENAME = "cover_letter_template.md"
PERSONAL_FILENAME = "personal.json"


@dataclass(frozen=True)
class PersonalInfo:
    full_name: str
    email: str
    phone: str | None
    location: str | None
    linkedin: str | None
    github: str | None
    languages: list[str]

    def as_contact_lines(self) -> str:
        lines = [f"Full name: {self.full_name}", f"Email: {self.email}"]
        if self.phone:
            lines.append(f"Phone: {self.phone}")
        if self.location:
            lines.append(f"Location: {self.location}")
        if self.linkedin:
            lines.append(f"LinkedIn: {self.linkedin}")
        if self.github:
            lines.append(f"GitHub: {self.github}")
        if self.languages:
            lines.append("Languages: " + ", ".join(self.languages))
        return "\n".join(lines)


@dataclass(frozen=True)
class Profile:
    personal: PersonalInfo
    master_cv_markdown: str
    cover_letter_template: str


def load_profile(profile_dir: str | Path) -> Profile:
    directory = Path(profile_dir)
    return Profile(
        personal=_load_personal(directory / PERSONAL_FILENAME),
        master_cv_markdown=_read_required_text(directory / MASTER_CV_FILENAME),
        cover_letter_template=_read_required_text(directory / COVER_LETTER_TEMPLATE_FILENAME),
    )


def _read_required_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise ProfileError(
            f"Profile file {path.name} was not found in {path.parent}. "
            "Create it before running; see SPEC section 3 for the expected files."
        )
    except UnicodeDecodeError:
        raise ProfileError(f"Profile file {path.name} is not valid UTF-8 text. Re-save it as UTF-8 and try again.")
    if not text:
        raise ProfileError(f"Profile file {path.name} is empty. Add your content and try again.")
    return text


def _load_personal(path: Path) -> PersonalInfo:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ProfileError(
            f"Profile file {path.name} was not found in {path.parent}. "
            "Create it before running; see SPEC section 3 for the expected files."
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProfileError(
            f"Profile file {path.name} is not valid JSON ({error}). Fix the syntax and try again."
        )
    return PersonalInfo(
        full_name=_require_text(data, "full_name", path),
        email=_require_text(data, "email", path),
        phone=_optional_text(data, "phone"),
        location=_optional_text(data, "location"),
        linkedin=_optional_text(data, "linkedin"),
        github=_optional_text(data, "github"),
        languages=_string_list(data.get("languages")),
    )


def _require_text(data: dict, key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(
            f"Profile file {path.name} is missing the required field '{key}'. Add it and try again."
        )
    return value.strip()


def _optional_text(data: dict, key: str) -> str | None:
    value = data.get(key)
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
