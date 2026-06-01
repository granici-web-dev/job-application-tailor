from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from anthropic import Anthropic
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, field_validator

from backend.config import Settings, frontend_origins, load_settings, make_anthropic_client
from backend.errors import ApplicationNotFoundError, TailorError, TrackerError
from backend.pipeline import TRACKER_FILENAME, run_pipeline
from backend.tracker import (
    ALLOWED_STATUSES,
    Application,
    read_applications,
    set_application_hidden,
    set_application_status,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

OUTPUT_DIR = Path("output")
PROFILE_DIR = Path("profile")


@dataclass(frozen=True)
class Paths:
    output_dir: Path
    profile_dir: Path


def get_settings() -> Settings:
    return load_settings()


def get_anthropic_client(settings: Settings = Depends(get_settings)) -> Anthropic:
    return make_anthropic_client(settings)


def get_paths() -> Paths:
    return Paths(output_dir=OUTPUT_DIR, profile_dir=PROFILE_DIR)


class GenerateRequest(BaseModel):
    url: str
    text: str | None = None
    lang: str | None = None


class GenerateResponse(BaseModel):
    id: int
    analysis: dict
    company: str
    cv_pdf: str
    cover_letter_pdf: str
    files: dict[str, str]


class ApplicationResponse(BaseModel):
    id: int
    company_name: str
    employee_count: str
    job_url: str
    employment_type: str
    job_title: str
    status: str
    created_on: str
    hidden: bool
    location: str | None
    files: dict[str, str] | None


class StatusUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _status_must_be_known(cls, value: str) -> str:
        if value not in ALLOWED_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_STATUSES)}")
        return value


class VisibilityUpdateRequest(BaseModel):
    hidden: bool


app = FastAPI(title="Job Application Tailor")
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApplicationNotFoundError)
async def _handle_application_not_found(request: Request, exc: ApplicationNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(TrackerError)
async def _handle_tracker_locked(request: Request, exc: TrackerError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(TailorError)
async def _handle_tailor_error(request: Request, exc: TailorError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.post("/generate", response_model=GenerateResponse)
def generate(
    request: GenerateRequest,
    settings: Settings = Depends(get_settings),
    client: Anthropic = Depends(get_anthropic_client),
    paths: Paths = Depends(get_paths),
) -> GenerateResponse:
    result = run_pipeline(
        job_url=request.url,
        job_text=request.text,
        output_dir=paths.output_dir,
        profile_dir=paths.profile_dir,
        client=client,
        model=settings.model,
        language=request.lang,
        today=date.today(),
    )
    company = result.company_dir.name
    cv_pdf = result.cv_pdf_path.name
    cover_letter_pdf = result.cover_letter_pdf_path.name
    return GenerateResponse(
        id=result.tracker_row,
        analysis=result.analysis.to_dict(),
        company=company,
        cv_pdf=cv_pdf,
        cover_letter_pdf=cover_letter_pdf,
        files={
            "cv": f"/files/{company}/{cv_pdf}",
            "cover_letter": f"/files/{company}/{cover_letter_pdf}",
        },
    )


@app.get("/applications", response_model=list[ApplicationResponse])
def list_applications(
    include_hidden: bool = False,
    paths: Paths = Depends(get_paths),
) -> list[ApplicationResponse]:
    applications = read_applications(paths.output_dir / TRACKER_FILENAME, include_hidden=include_hidden)
    return [_to_response(application) for application in applications]


@app.patch("/applications/{application_id}/status", response_model=ApplicationResponse)
def update_status(
    application_id: int,
    body: StatusUpdateRequest,
    paths: Paths = Depends(get_paths),
) -> ApplicationResponse:
    tracker_path = paths.output_dir / TRACKER_FILENAME
    set_application_status(tracker_path, application_id, body.status)
    return _to_response(_find_application(tracker_path, application_id))


@app.patch("/applications/{application_id}/visibility", response_model=ApplicationResponse)
def update_visibility(
    application_id: int,
    body: VisibilityUpdateRequest,
    paths: Paths = Depends(get_paths),
) -> ApplicationResponse:
    tracker_path = paths.output_dir / TRACKER_FILENAME
    set_application_hidden(tracker_path, application_id, body.hidden)
    return _to_response(_find_application(tracker_path, application_id))


def _find_application(tracker_path: Path, application_id: int) -> Application:
    for application in read_applications(tracker_path, include_hidden=True):
        if application.id == application_id:
            return application
    raise ApplicationNotFoundError(f"No application with id {application_id} in the tracker.")


def _to_response(application: Application) -> ApplicationResponse:
    files = None
    if application.cv_file and application.cover_letter_file:
        files = {
            "cv": f"/files/{application.cv_file}",
            "cover_letter": f"/files/{application.cover_letter_file}",
        }
    return ApplicationResponse(
        id=application.id,
        company_name=application.company_name,
        employee_count=application.employee_count,
        job_url=application.job_url,
        employment_type=application.employment_type,
        job_title=application.job_title,
        status=application.status,
        created_on=application.created_on,
        hidden=application.hidden,
        location=application.location,
        files=files,
    )


@app.get("/files/{company}/{filename}")
def serve_file(company: str, filename: str, paths: Paths = Depends(get_paths)) -> FileResponse:
    output_root = paths.output_dir.resolve()
    candidate = (output_root / company / filename).resolve()
    if not candidate.is_relative_to(output_root) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(candidate, media_type="application/pdf", filename=candidate.name)
