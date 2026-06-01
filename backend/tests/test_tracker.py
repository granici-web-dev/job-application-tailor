from datetime import date
from unittest.mock import patch

import pytest
from openpyxl import load_workbook

from backend.errors import TrackerError
from backend.models import JobAnalysis
from backend.tracker import EMPLOYEE_COUNT_UNKNOWN, HEADERS, STATUS_NOT_SENT, append_application


def _analysis(**overrides):
    data = {
        "company_name": "Acme GmbH",
        "job_title": "Backend Engineer",
        "employment_type": "remote",
        "employee_count": "50-200",
    }
    data.update(overrides)
    return JobAnalysis.from_response_dict(data)


def test_append_creates_file_with_header_when_missing(tmp_path):
    path = tmp_path / "tracker.xlsx"

    append_application(path, _analysis(), job_url="https://x/1", created_on=date(2026, 6, 1))

    assert path.exists()
    sheet = load_workbook(path).active
    assert [cell.value for cell in sheet[1]] == HEADERS
    assert sheet[1][0].font.bold is True
    assert sheet.freeze_panes == "A2"


def test_append_adds_row_with_values_and_na_employee_count(tmp_path):
    path = tmp_path / "tracker.xlsx"

    row = append_application(path, _analysis(employee_count=None), job_url="https://x/1", created_on=date(2026, 6, 1))

    assert row == 2
    sheet = load_workbook(path).active
    assert [cell.value for cell in sheet[2]] == [
        "Acme GmbH",
        EMPLOYEE_COUNT_UNKNOWN,
        "https://x/1",
        "remote",
        "Backend Engineer",
        STATUS_NOT_SENT,
        "2026-06-01",
    ]


def test_append_appends_without_overwriting(tmp_path):
    path = tmp_path / "tracker.xlsx"

    append_application(path, _analysis(company_name="First"), job_url="https://x/1", created_on=date(2026, 6, 1))
    second = append_application(path, _analysis(company_name="Second"), job_url="https://x/2", created_on=date(2026, 6, 2))

    assert second == 3
    sheet = load_workbook(path).active
    assert sheet["A2"].value == "First"
    assert sheet["A3"].value == "Second"
    assert sheet.max_row == 3


def test_status_column_dropdown_is_bound_to_the_status_column(tmp_path):
    path = tmp_path / "tracker.xlsx"
    append_application(path, _analysis(), job_url="https://x/1", created_on=date(2026, 6, 1))
    sheet = load_workbook(path).active

    status_column = next(cell.column_letter for cell in sheet[1] if cell.value == "Статус")
    assert status_column == "F"

    status_dropdowns = [
        dv for dv in sheet.data_validations.dataValidation if dv.formula1 and "ОТПРАВЛЕНО" in dv.formula1
    ]
    assert len(status_dropdowns) == 1
    assert str(status_dropdowns[0].sqref) == f"{status_column}2:{status_column}1000"
    assert "НЕ ОТПРАВЛЕНО" in status_dropdowns[0].formula1


def test_append_default_status_is_not_sent(tmp_path):
    path = tmp_path / "tracker.xlsx"
    append_application(path, _analysis(), job_url="https://x/1", created_on=date(2026, 6, 1))
    sheet = load_workbook(path).active

    assert sheet["F2"].value == STATUS_NOT_SENT


def test_append_raises_tracker_error_when_file_is_locked(tmp_path):
    path = tmp_path / "tracker.xlsx"

    with patch("backend.tracker.Workbook.save", side_effect=PermissionError):
        with pytest.raises(TrackerError, match="open in Excel"):
            append_application(path, _analysis(), job_url="https://x/1", created_on=date(2026, 6, 1))
