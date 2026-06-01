from __future__ import annotations

from dataclasses import asdict, dataclass

from backend.errors import JobAnalysisError

EMPLOYMENT_TYPES = frozenset({"remote", "onsite", "hybrid", "unknown"})


@dataclass(frozen=True)
class JobAnalysis:
    company_name: str
    job_title: str
    employment_type: str
    employee_count: str | None
    location: str | None
    hard_skills: list[str]
    soft_skills: list[str]
    keywords: list[str]
    key_responsibilities: list[str]
    language_requirements: list[str]

    @classmethod
    def from_response_dict(cls, data: dict) -> "JobAnalysis":
        employment_type = data.get("employment_type")
        if employment_type not in EMPLOYMENT_TYPES:
            employment_type = "unknown"
        return cls(
            company_name=_require_text(data.get("company_name"), "company_name"),
            job_title=_require_text(data.get("job_title"), "job_title"),
            employment_type=employment_type,
            employee_count=_optional_text(data.get("employee_count")),
            location=_optional_text(data.get("location")),
            hard_skills=_string_list(data.get("hard_skills")),
            soft_skills=_string_list(data.get("soft_skills")),
            keywords=_string_list(data.get("keywords")),
            key_responsibilities=_string_list(data.get("key_responsibilities")),
            language_requirements=_string_list(data.get("language_requirements")),
        )

    def to_dict(self) -> dict:
        return asdict(self)


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JobAnalysisError(
            f"The job analysis is missing the required field '{field_name}'. "
            "Re-run the command to try again."
        )
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
