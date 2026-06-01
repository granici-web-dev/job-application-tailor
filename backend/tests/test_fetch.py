from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from backend.errors import JobFetchError
from backend.fetch import extract_main_text, fetch_job_text, read_job_text_file

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "job_posting.html").read_text(encoding="utf-8")


def _response(text, content_type="text/html; charset=utf-8", apparent_encoding="utf-8"):
    response = Mock()
    response.text = text
    response.headers = {"Content-Type": content_type}
    response.apparent_encoding = apparent_encoding
    response.raise_for_status = Mock()
    return response


def test_fetch_extracts_main_text_without_scripts_or_styles():
    text = extract_main_text(FIXTURE_HTML)

    assert "Senior Backend Engineer" in text
    assert "Design REST APIs with FastAPI" in text
    assert "TRACKING_PIXEL_NOISE" not in text
    assert "display: none" not in text


def test_fetch_job_text_returns_extracted_body():
    with patch("backend.fetch.requests.get", return_value=_response(FIXTURE_HTML)):
        text = fetch_job_text("https://example.com/jobs/1")

    assert "Acme GmbH is hiring" in text


def test_fetch_raises_job_fetch_error_on_empty_content():
    with patch("backend.fetch.requests.get", return_value=_response("<html><body></body></html>")):
        with pytest.raises(JobFetchError, match="--text-file"):
            fetch_job_text("https://example.com/jobs/empty")


def test_fetch_raises_job_fetch_error_on_request_failure():
    with patch("backend.fetch.requests.get", side_effect=requests.ConnectionError("refused")):
        with pytest.raises(JobFetchError, match="Could not download"):
            fetch_job_text("https://example.com/jobs/down")


def test_fetch_rejects_url_without_http_scheme():
    with patch("backend.fetch.requests.get") as get:
        with pytest.raises(JobFetchError, match="http://"):
            fetch_job_text("linkedin.com/jobs/123")
    get.assert_not_called()


def test_fetch_rejects_non_html_content_type():
    response = _response("%PDF-1.7 binary noise", content_type="application/pdf")

    with patch("backend.fetch.requests.get", return_value=response):
        with pytest.raises(JobFetchError, match="application/pdf"):
            fetch_job_text("https://example.com/jobs/posting.pdf")


def test_fetch_applies_detected_encoding_when_charset_absent():
    response = _response(FIXTURE_HTML, content_type="text/html", apparent_encoding="utf-8")
    response.encoding = "ISO-8859-1"

    with patch("backend.fetch.requests.get", return_value=response):
        fetch_job_text("https://example.com/jobs/de")

    assert response.encoding == "utf-8"


def test_fetch_keeps_declared_charset_encoding():
    response = _response(FIXTURE_HTML, content_type="text/html; charset=utf-8")
    response.encoding = "utf-8"

    with patch("backend.fetch.requests.get", return_value=response):
        fetch_job_text("https://example.com/jobs/en")

    assert response.encoding == "utf-8"


def test_read_job_text_file_reads_stripped_text(tmp_path):
    job_file = tmp_path / "posting.txt"
    job_file.write_text("  Backend Engineer at Acme  \n", encoding="utf-8")

    assert read_job_text_file(str(job_file)) == "Backend Engineer at Acme"


def test_read_job_text_file_raises_on_empty(tmp_path):
    job_file = tmp_path / "empty.txt"
    job_file.write_text("   \n", encoding="utf-8")

    with pytest.raises(JobFetchError, match="empty"):
        read_job_text_file(str(job_file))


def test_read_job_text_file_raises_on_non_utf8(tmp_path):
    job_file = tmp_path / "latin1.txt"
    job_file.write_bytes("Schöne Stelle bei Café GmbH".encode("latin-1"))

    with pytest.raises(JobFetchError, match="UTF-8"):
        read_job_text_file(str(job_file))
