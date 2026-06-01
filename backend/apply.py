from __future__ import annotations

import argparse
import json
import sys

from backend.analyze import analyze_job
from backend.config import load_settings, make_anthropic_client
from backend.errors import TailorError
from backend.fetch import fetch_job_text, read_job_text_file


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        settings = load_settings()
        job_text = read_job_text_file(args.text_file) if args.text_file else fetch_job_text(args.url)
        client = make_anthropic_client(settings)
        analysis = analyze_job(job_text, client=client, model=settings.model)
    except TailorError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m backend.apply",
        description="Analyze a job posting and print the extracted details as JSON.",
    )
    parser.add_argument("url", help="URL of the job posting")
    parser.add_argument(
        "--text-file",
        help="Read the posting text from this file instead of downloading the URL.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
