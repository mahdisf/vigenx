"""CSV history log: one row per pipeline run — acts as a scalable spreadsheet."""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)

COLUMNS = [
    "date",
    "pipeline",
    "game",
    "video_id",
    "title",
    "source",
    "output_path",
    "manifest_path",
    "metadata_path",
    "status",
]


def append_history_row(
    csv_path: str,
    *,
    pipeline: str,
    game: str = "",
    video_id: str = "",
    title: str = "",
    source: str = "",
    output_path: str = "",
    manifest_path: str = "",
    metadata_path: str = "",
    status: str = "done",
) -> None:
    """Append one row to the history CSV, creating the file and header if needed."""
    parent = os.path.dirname(csv_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    write_header = not os.path.isfile(csv_path)
    try:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            if write_header:
                writer.writeheader()
            writer.writerow(
                {
                    "date": datetime.now().isoformat(timespec="seconds"),
                    "pipeline": pipeline,
                    "game": game,
                    "video_id": str(video_id),
                    "title": title,
                    "source": source,
                    "output_path": output_path,
                    "manifest_path": manifest_path,
                    "metadata_path": metadata_path,
                    "status": status,
                }
            )
        log.debug("History logged to %s", csv_path)
    except OSError as exc:
        log.warning("Could not write history CSV: %s", exc)


def read_history(csv_path: str) -> list[dict]:
    """Return all history rows as a list of dicts. Returns [] if file missing."""
    if not os.path.isfile(csv_path):
        return []
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError as exc:
        log.warning("Could not read history CSV: %s", exc)
        return []
