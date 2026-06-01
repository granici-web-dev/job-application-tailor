from __future__ import annotations

from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from backend.errors import JobFetchError

REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
STRIPPED_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]
MINIMUM_READABLE_LENGTH = 200


def fetch_job_text(url: str) -> str:
    if urlparse(url).scheme.lower() not in ("http", "https"):
        raise JobFetchError(
            f"'{url}' is not a valid web address. Pass a full link starting with http:// or https://, "
            "or save the posting text to a file and pass it with --text-file."
        )
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

    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type and not content_type.startswith("text/"):
        raise JobFetchError(
            f"The link at {url} returned {content_type.split(';')[0]}, not a web page. "
            "Open the posting in a browser, copy its text into a file, and pass it with --text-file."
        )
    if "charset=" not in content_type:
        response.encoding = response.apparent_encoding

    text = extract_main_text(response.text)
    if len(text) < MINIMUM_READABLE_LENGTH:
        raise JobFetchError(
            f"The page at {url} returned almost no readable text. It likely needs JavaScript "
            "or blocks bots. Copy the posting text into a file and pass it with --text-file."
        )
    return text


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
