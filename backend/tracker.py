from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.worksheet.datavalidation import DataValidation

from backend.errors import TrackerError
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
STATUS_SENT = "ОТПРАВЛЕНО"
STATUS_NOT_SENT = "НЕ ОТПРАВЛЕНО"
STATUS_RANGE = f"{STATUS_COLUMN}2:{STATUS_COLUMN}1000"
EMPLOYEE_COUNT_UNKNOWN = "н/д"
COLUMN_WIDTHS = {"A": 28, "B": 18, "C": 42, "D": 16, "E": 32, "F": 18, "G": 14}


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


def _open_or_create(tracker_path: Path) -> Workbook:
    if not tracker_path.exists():
        return _create_workbook()
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
