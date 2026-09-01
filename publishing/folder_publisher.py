"""Organize rendered videos into a dated render tree: /renders/YYYY-MM-DD/.

Copies the video plus any sidecar files produced by the export block (rights
manifest, metadata JSON, thumbnail) next to it. Pure stdlib.
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import date
from typing import List, Optional

log = logging.getLogger(__name__)

_SIDECAR_SUFFIXES = ("_rights.json", "_metadata.json", "_thumb.jpg", "_details.txt")


def render_dir_for(renders_dir: str = "renders", when: Optional[date] = None) -> str:
    """Return (and create) the dated subfolder for a render."""
    day = (when or date.today()).isoformat()
    path = os.path.join(renders_dir, day)
    os.makedirs(path, exist_ok=True)
    return path


def _sidecars(video_path: str) -> List[str]:
    base, _ = os.path.splitext(video_path)
    found = []
    for suffix in _SIDECAR_SUFFIXES:
        cand = base + suffix
        if os.path.isfile(cand):
            found.append(cand)
    return found


def publish_to_folder(
    video_path: str,
    renders_dir: str = "renders",
    when: Optional[date] = None,
    move: bool = False,
) -> str:
    """Copy (or move) the video and sidecars into the dated render tree.

    Returns the destination video path.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    dest_dir = render_dir_for(renders_dir, when)
    op = shutil.move if move else shutil.copy2

    for sidecar in _sidecars(video_path):
        try:
            op(sidecar, os.path.join(dest_dir, os.path.basename(sidecar)))
        except Exception as exc:  # Sidecars are best-effort.
            log.debug("Sidecar publish failed for %s: %s", sidecar, exc)

    dest_video = os.path.join(dest_dir, os.path.basename(video_path))
    op(video_path, dest_video)
    log.info("Published render -> %s", dest_video)
    return dest_video


__all__ = ["publish_to_folder", "render_dir_for"]
