from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from backend.errors import JobFetchError, JobTextMissingError
from backend.fetch import BoardPosting, extract_main_text, fetch_job_text, job_board_posting, read_job_text_file

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


def test_the_page_title_is_not_part_of_the_posting_text():
    html = "<html><head><title>Karriere | Acme GmbH</title></head><body><p>Initiativbewerbung</p></body></html>"

    assert extract_main_text(html) == "Initiativbewerbung"


ASHBY_JOB = "7458d4e9-da2e-47bd-98cb-adfda43d42b2"
LEVER_JOB = "ad208490-4052-4f91-a57e-433f2d1e484b"
COMPANY_PAGE = "<html><body><h1>Karriere bei Acme</h1><p>" + "Wir sind ein Team aus Köln. " * 20 + "</p></body></html>"
DESCRIPTION = "Wir suchen eine Frontend-Entwicklerin mit React und TypeScript. " * 5


def _json(data):
    response = _response("", content_type="application/json")
    response.json = Mock(return_value=data)
    return response


def _routed(routes):
    """A requests.get that answers by URL prefix, and fails on any other."""

    def get(url, **kwargs):
        for prefix, response in routes.items():
            if url.startswith(prefix):
                return response
        raise AssertionError(f"unexpected request to {url}")

    return get


@pytest.mark.parametrize(
    ("url", "posting"),
    [
        (f"https://jobs.ashbyhq.com/acme/{ASHBY_JOB}", BoardPosting("ashby", "acme", ASHBY_JOB)),
        (f"https://acme.com/careers?ashby_jid={ASHBY_JOB}", BoardPosting("ashby", None, ASHBY_JOB)),
        ("https://boards.greenhouse.io/acme/jobs/123", BoardPosting("greenhouse", "acme", "123")),
        ("https://job-boards.greenhouse.io/acme/jobs/123", BoardPosting("greenhouse", "acme", "123")),
        ("https://acme.com/positions/123?gh_jid=123", BoardPosting("greenhouse", None, "123")),
        (f"https://jobs.lever.co/acme/{LEVER_JOB}", BoardPosting("lever", "acme", LEVER_JOB)),
        ("https://acme.com/jobs?lever-source=LinkedIn", BoardPosting("lever", None, None)),
        ("https://acme.jobs.personio.de/job/1834171?language=de", BoardPosting("personio", "acme", "1834171")),
        ("https://example.com/jobs/1", None),
    ],
)
def test_a_job_platform_is_recognised_by_its_domain_or_parameter(url, posting):
    assert job_board_posting(url) == posting


def test_an_ashby_posting_is_read_through_its_api_not_the_page():
    board = {"jobs": [{"id": "other", "title": "Other"}, {"id": ASHBY_JOB, "title": "Frontend Developer", "location": "Köln", "descriptionPlain": DESCRIPTION}]}
    get = _routed({"https://api.ashbyhq.com/posting-api/job-board/acme": _json(board)})

    with patch("backend.fetch.requests.get", side_effect=get):
        text = fetch_job_text(f"https://jobs.ashbyhq.com/acme/{ASHBY_JOB}")

    assert text.startswith("Company (job board): acme\n\nFrontend Developer\n\nKöln\n\nWir suchen")


def test_a_company_page_embedding_greenhouse_gives_its_board_to_the_api():
    page = COMPANY_PAGE.replace("</body>", '<script src="https://boards.greenhouse.io/embed/job_board/js?for=acme"></script></body>')
    job = {"company_name": "Acme GmbH", "title": "Frontend Developer", "location": {"name": "Köln"}, "content": "&lt;p&gt;" + DESCRIPTION + "&lt;/p&gt;"}
    get = _routed({
        "https://acme.com/": _response(page),
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs/123": _json(job),
    })

    with patch("backend.fetch.requests.get", side_effect=get):
        text = fetch_job_text("https://acme.com/positions/123?gh_jid=123")

    assert text.startswith("Acme GmbH\n\nFrontend Developer\n\nKöln\n\nWir suchen")
    assert "<p>" not in text


def test_a_lever_posting_carries_its_lists():
    job = {"text": "Frontend Developer", "categories": {"location": "Berlin"}, "descriptionPlain": DESCRIPTION,
           "lists": [{"text": "Requirements", "content": "<li>React</li><li>TypeScript</li>"}], "additionalPlain": ""}
    get = _routed({f"https://api.lever.co/v0/postings/acme/{LEVER_JOB}": _json(job)})

    with patch("backend.fetch.requests.get", side_effect=get):
        text = fetch_job_text(f"https://jobs.lever.co/acme/{LEVER_JOB}")

    assert "Requirements\nReact\nTypeScript" in text


def test_a_platform_api_without_the_posting_falls_back_to_the_page():
    get = _routed({
        "https://api.ashbyhq.com/": _json({"jobs": []}),
        "https://jobs.ashbyhq.com/": _response(FIXTURE_HTML),
    })

    with patch("backend.fetch.requests.get", side_effect=get):
        text = fetch_job_text(f"https://jobs.ashbyhq.com/acme/{ASHBY_JOB}")

    assert "Acme GmbH is hiring" in text


def test_an_empty_platform_page_asks_for_the_text():
    get = _routed({"https://acme.com/": _response("<html><body><div id='root'></div></body></html>")})

    with patch("backend.fetch.requests.get", side_effect=get):
        with pytest.raises(JobTextMissingError, match="Вакансия загружается через JavaScript"):
            fetch_job_text(f"https://acme.com/careers?ashby_jid={ASHBY_JOB}")
