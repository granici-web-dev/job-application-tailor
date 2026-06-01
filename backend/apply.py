from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from backend.config import load_settings, make_anthropic_client
from backend.errors import TailorError
from backend.fetch import read_job_text_file
from backend.pipeline import PipelineResult, run_pipeline

PROFILE_DIR = Path("profile")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        settings = load_settings()
        client = make_anthropic_client(settings)
        job_text = read_job_text_file(args.text_file) if args.text_file else None
        result = run_pipeline(
            job_url=args.url,
            job_text=job_text,
            output_dir=Path(args.output_dir),
            profile_dir=PROFILE_DIR,
            client=client,
            model=settings.model,
            language=args.lang,
            today=date.today(),
            include_photo=args.include_photo,
        )
    except TailorError as error:
        print(str(error), file=sys.stderr)
        return 1
    _print_summary(result)
    return 0


def _print_summary(result: PipelineResult) -> None:
    print()
    print(f"Company:  {result.analysis.company_name}")
    print(f"Position: {result.analysis.job_title}")
    print("Saved:")
    print(f"  {result.cv_pdf_path}")
    print(f"  {result.cover_letter_pdf_path}")
    print(f"Tracker:  {result.tracker_path} (row {result.tracker_row}, status НЕ ОТПРАВЛЕНО)")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m backend.apply",
        description="Tailor a CV and cover letter to a job posting and record the application.",
    )
    parser.add_argument("url", help="URL of the job posting")
    parser.add_argument(
        "--text-file",
        help="Read the posting text from this file instead of downloading the URL.",
    )
    parser.add_argument(
        "--lang",
        help="Force the output language. Defaults to the posting's language.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Root output folder. Defaults to ./output.",
    )
    parser.add_argument(
        "--no-photo",
        dest="include_photo",
        action="store_false",
        help="Leave the photo out of the CV PDF, for portals that penalize photos.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
