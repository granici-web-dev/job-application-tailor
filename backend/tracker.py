from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.worksheet.datavalidation import DataValidation

from backend.errors import ApplicationNotFoundError, TrackerError
from backend.models import JobAnalysis

HEADERS = [
    "Название фирмы",
    "Сколько работников",
    "Линк на вакансию",
    "Тип занятости",
    "Название должности",
    "Статус",
    "Дата создания",
]
STATUS_COLUMN = "F"
STATUS_COLUMN_INDEX = 6
STATUS_SENT = "ОТПРАВЛЕНО"
STATUS_NOT_SENT = "НЕ ОТПРАВЛЕНО"
STATUS_RANGE = f"{STATUS_COLUMN}2:{STATUS_COLUMN}1000"
ALLOWED_STATUSES = frozenset({STATUS_SENT, STATUS_NOT_SENT})
EMPLOYEE_COUNT_UNKNOWN = "н/д"
COLUMN_WIDTHS = {"A": 28, "B": 18, "C": 42, "D": 16, "E": 32, "F": 18, "G": 14}
DATA_START_ROW = 2


@dataclass(frozen=True)
class Application:
    id: int
    company_name: str
    employee_count: str
    job_url: str
    employment_type: str
    job_title: str
    status: str
    created_on: str


def append_application(
    tracker_path: Path,
    analysis: JobAnalysis,
    *,
    job_url: str,
    created_on: date,
) -> int:
    workbook = _open_or_create(tracker_path)
    sheet = workbook.active
    sheet.append(
        [
            analysis.company_name,
            analysis.employee_count or EMPLOYEE_COUNT_UNKNOWN,
            job_url,
            analysis.employment_type,
            analysis.job_title,
            STATUS_NOT_SENT,
            created_on.isoformat(),
        ]
    )
    appended_row = sheet.max_row
    try:
        workbook.save(tracker_path)
    except PermissionError:
        raise TrackerError(
            f"Could not write the tracker at {tracker_path}. It is probably open in Excel. "
            "Close it and run again."
        )
    return appended_row


def read_applications(tracker_path: Path) -> list[Application]:
    if not tracker_path.exists():
        return []
    sheet = _load_workbook(tracker_path).active
    applications = []
    for row in range(DATA_START_ROW, sheet.max_row + 1):
        values = [sheet.cell(row=row, column=column).value for column in range(1, len(HEADERS) + 1)]
        if values[0] is None:
            continue
        applications.append(
            Application(
                id=row,
                company_name=_cell_text(values[0]),
                employee_count=_cell_text(values[1]),
                job_url=_cell_text(values[2]),
                employment_type=_cell_text(values[3]),
                job_title=_cell_text(values[4]),
                status=_cell_text(values[5]),
                created_on=_cell_text(values[6]),
            )
        )
    return applications


def set_application_status(tracker_path: Path, application_id: int, status: str) -> None:
    if not tracker_path.exists():
        raise ApplicationNotFoundError(f"No application with id {application_id} exists yet.")
    workbook = _load_workbook(tracker_path)
    sheet = workbook.active
    if application_id < DATA_START_ROW or application_id > sheet.max_row:
        raise ApplicationNotFoundError(f"No application with id {application_id} in the tracker.")
    sheet.cell(row=application_id, column=STATUS_COLUMN_INDEX).value = status
    try:
        workbook.save(tracker_path)
    except PermissionError:
        raise TrackerError(
            f"Could not write the tracker at {tracker_path}. It is probably open in Excel. "
            "Close it and run again."
        )


def _cell_text(value: object) -> str:
    return "" if value is None else str(value)


def _open_or_create(tracker_path: Path) -> Workbook:
    if not tracker_path.exists():
        return _create_workbook()
    return _load_workbook(tracker_path)


def _load_workbook(tracker_path: Path) -> Workbook:
    try:
        return load_workbook(tracker_path)
    except PermissionError:
        raise TrackerError(
            f"Could not open the tracker at {tracker_path}. It is probably open in Excel. "
            "Close it and run again."
        )


def _create_workbook() -> Workbook:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Applications"
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    for column, width in COLUMN_WIDTHS.items():
        sheet.column_dimensions[column].width = width
    status_dropdown = DataValidation(
        type="list",
        formula1=f'"{STATUS_SENT},{STATUS_NOT_SENT}"',
        allow_blank=False,
    )
    sheet.add_data_validation(status_dropdown)
    status_dropdown.add(STATUS_RANGE)
    return workbook
