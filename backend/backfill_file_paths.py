from __future__ import annotations

from pathlib import Path

from backend.pipeline import TRACKER_FILENAME
from backend.tracker import backfill_file_paths

OUTPUT_DIR = Path("output")


def main() -> int:
    tracker_path = OUTPUT_DIR / TRACKER_FILENAME
    backfilled = backfill_file_paths(tracker_path, OUTPUT_DIR)
    if backfilled:
        print(f"Backfilled file paths for rows: {', '.join(str(row) for row in backfilled)}")
    else:
        print("No rows needed backfilling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
