from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, replace
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from backend.errors import JobFetchError, JobTextMissingError

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
# The page title goes too: it names the site as often as the position, and a missing
# position is asked for by hand rather than taken from it.
STRIPPED_TAGS = ["title", "script", "style", "noscript", "nav", "header", "footer", "aside", "form"]
MINIMUM_READABLE_LENGTH = 200


@dataclass(frozen=True)
class BoardPosting:
    """A posting on a job platform that renders it with JavaScript, read through its own API.

    `board` is the company's name on the platform, `job_id` the posting's; either is None when
    the link does not carry it (a company page with ?gh_jid=…), and then the page may.
    """

    platform: str
    board: str | None
    job_id: str | None


ASHBY_HOST = "jobs.ashbyhq.com"
GREENHOUSE_HOSTS = ("boards.greenhouse.io", "job-boards.greenhouse.io")
LEVER_HOSTS = ("jobs.lever.co", "jobs.eu.lever.co")
PERSONIO_HOST = re.compile(r"^([\w-]+)\.jobs\.personio\.(?:de|com)$")
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# Where a company page that embeds the platform names its board.
BOARD_IN_PAGE = {
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([\w.-]+)"),
    "greenhouse": re.compile(
        r"greenhouse\.io/(?:embed/job_(?:board|app)(?:/js)?\?for=|v1/boards/)?(?!embed\b)([\w-]+)"
    ),
    "lever": re.compile(rf"jobs\.(?:eu\.)?lever\.co/([\w.-]+)/({UUID})"),
}


def job_board_posting(url: str) -> BoardPosting | None:
    """The platform posting a link points at, if the link carries a platform's sign."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    query = {key.lower(): values[0] for key, values in parse_qs(parsed.query).items()}
    if host == ASHBY_HOST:
        return BoardPosting("ashby", _at(parts, 0), _at(parts, 1))
    if host in GREENHOUSE_HOSTS:
        if parts[:1] == ["embed"]:
            return BoardPosting("greenhouse", query.get("for"), query.get("token"))
        return BoardPosting("greenhouse", _at(parts, 0), _at(parts, 2) if _at(parts, 1) == "jobs" else None)
    if host in LEVER_HOSTS:
        return BoardPosting("lever", _at(parts, 0), _at(parts, 1))
    personio = PERSONIO_HOST.match(host)
    if personio:
        return BoardPosting("personio", personio.group(1), _at(parts, 1) if _at(parts, 0) == "job" else None)
    if "ashby_jid" in query:
        return BoardPosting("ashby", None, query["ashby_jid"])
    if "gh_jid" in query:
        return BoardPosting("greenhouse", None, query["gh_jid"])
    if any("lever" in key for key in query):
        return BoardPosting("lever", None, None)
    return None


def fetch_job_text(url: str) -> str:
    if urlparse(url).scheme.lower() not in ("http", "https"):
        raise JobFetchError(
            f"'{url}' is not a valid web address. Pass a full link starting with http:// or https://, "
            "or save the posting text to a file and pass it with --text-file."
        )
    posting = job_board_posting(url)
    if posting and posting.board and posting.job_id:
        text = _board_text(posting)
        if text:
            return text

    response = _get(url)

    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type and not content_type.startswith("text/"):
        raise JobFetchError(
            f"The link at {url} returned {content_type.split(';')[0]}, not a web page. "
            "Open the posting in a browser, copy its text into a file, and pass it with --text-file."
        )
    if "charset=" not in content_type:
        response.encoding = response.apparent_encoding

    if posting and not (posting.board and posting.job_id):
        # A company page that embeds the platform: the board's name is in its markup.
        found = BOARD_IN_PAGE.get(posting.platform)
        match = found.search(response.text) if found else None
        if match:
            job_id = posting.job_id or (match.group(2) if match.lastindex and match.lastindex > 1 else None)
            text = _board_text(replace(posting, board=match.group(1), job_id=job_id)) if job_id else None
            if text:
                return text

    text = extract_main_text(response.text)
    if len(text) < MINIMUM_READABLE_LENGTH:
        if posting:
            raise JobTextMissingError()
        raise JobFetchError(
            f"The page at {url} returned almost no readable text. It likely needs JavaScript "
            "or blocks bots. Copy the posting text into a file and pass it with --text-file."
        )
    return text


def _get(url: str) -> requests.Response:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise JobFetchError(
            f"Could not download the job posting at {url} ({error}). "
            "Save the posting text to a file and pass it with --text-file instead."
        ) from error
    return response


def _board_text(posting: BoardPosting) -> str | None:
    """The posting's text from the platform's public API, or None when it does not give it."""
    reader = {"ashby": _ashby_text, "greenhouse": _greenhouse_text, "lever": _lever_text, "personio": _personio_text}
    try:
        text = reader[posting.platform](posting.board, posting.job_id)
    except (JobFetchError, ValueError, KeyError, TypeError, ElementTree.ParseError) as error:
        logger.warning("Could not read the %s posting %s/%s: %s", posting.platform, posting.board, posting.job_id, error)
        return None
    if text and len(text) >= MINIMUM_READABLE_LENGTH:
        logger.info("Read the posting through the %s API (%s/%s)", posting.platform, posting.board, posting.job_id)
        return text
    return None


def _ashby_text(board: str, job_id: str) -> str | None:
    jobs = _get(f"https://api.ashbyhq.com/posting-api/job-board/{board}").json()["jobs"]
    job = next((job for job in jobs if job.get("id") == job_id), None)
    if job is None:
        return None
    return _joined(f"Company (job board): {board}", job.get("title"), job.get("location"), job.get("descriptionPlain"))


def _greenhouse_text(board: str, job_id: str) -> str | None:
    job = _get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}").json()
    return _joined(
        job.get("company_name") or f"Company (job board): {board}",
        job.get("title"),
        (job.get("location") or {}).get("name"),
        # The content is HTML, escaped once more.
        _html_text(html.unescape(job.get("content") or "")),
    )


def _lever_text(board: str, job_id: str) -> str | None:
    job = _get(f"https://api.lever.co/v0/postings/{board}/{job_id}").json()
    lists = [f"{item.get('text', '')}\n{_html_text(item.get('content', ''))}" for item in job.get("lists") or []]
    return _joined(
        f"Company (job board): {board}",
        job.get("text"),
        (job.get("categories") or {}).get("location"),
        job.get("descriptionPlain"),
        *lists,
        job.get("additionalPlain"),
    )


def _personio_text(board: str, job_id: str) -> str | None:
    feed = ElementTree.fromstring(_get(f"https://{board}.jobs.personio.de/xml").content)
    position = next((item for item in feed.iter("position") if item.findtext("id") == job_id), None)
    if position is None:
        return None
    descriptions = [
        f"{item.findtext('name') or ''}\n{_html_text(item.findtext('value') or '')}"
        for item in position.iter("jobDescription")
    ]
    if not descriptions:
        # The feed may list the position without its text; the job's own page has it.
        return extract_main_text(_get(f"https://{board}.jobs.personio.de/job/{job_id}").text)
    return _joined(
        position.findtext("subcompany") or f"Company (job board): {board}",
        position.findtext("name"),
        position.findtext("office"),
        *descriptions,
    )


def _html_text(markup: str) -> str:
    return BeautifulSoup(markup, "html.parser").get_text(separator="\n", strip=True)


def _joined(*parts: str | None) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def _at(parts: list[str], index: int) -> str | None:
    return parts[index] if len(parts) > index else None


def extract_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(STRIPPED_TAGS):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def read_job_text_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read().strip()
    except OSError as error:
        raise JobFetchError(
            f"Could not read the job text file at {path} ({error}). Check the path and try again."
        ) from error
    except UnicodeDecodeError as error:
        raise JobFetchError(
            f"The job text file at {path} is not valid UTF-8 text. Re-save it as UTF-8 and try again."
        ) from error
    if not text:
        raise JobFetchError(
            f"The job text file at {path} is empty. Add the posting text and try again."
        )
    return text
