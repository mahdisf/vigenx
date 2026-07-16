"""Helpers for fast WYSIWYG previews and draft renders.

These keep the preview path cheap:
  * :func:`extract_frame` pulls a single JPEG frame at time ``t`` via ffmpeg
    (optionally downscaled) so overlay/style blocks can composite onto it.
  * :func:`make_draft_clip` builds a short, scaled-down subclip used for
    ``clip``-kind block previews and whole-graph draft renders.
  * :func:`params_hash` produces a stable key so the executor can memoize
    upstream node results across param tweaks.

Both ffmpeg helpers shell out to keep the dependency surface identical to the rest
of ``core/`` (which already relies on ffmpeg on PATH).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from typing import Any, Optional


def params_hash(*parts: Any) -> str:
    """Stable short hash of arbitrary JSON-serializable parts."""
    blob = json.dumps(parts, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:16]


def extract_frame(
    video_path: str,
    t: float,
    out_path: str,
    max_width: Optional[int] = None,
) -> str:
    """Write a single JPEG frame sampled at ``t`` seconds. Returns ``out_path``."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    vf = []
    if max_width:
        # scale down only if wider than max_width; keep aspect, even dims
        vf.append(f"scale='min({max_width},iw)':-2")
    cmd = ["ffmpeg", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", video_path,
           "-frames:v", "1"]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-q:v", "3", out_path]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path


def make_draft_clip(
    video_path: str,
    out_path: str,
    start: float = 0.0,
    seconds: float = 4.0,
    scale_width: int = 480,
) -> str:
    """Write a short, low-res, ultrafast-encoded subclip. Returns ``out_path``."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{max(0.0, start):.3f}",
        "-t", f"{max(0.5, seconds):.3f}",
        "-i", video_path,
        "-vf", f"scale={scale_width}:-2",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "96k",
        out_path,
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path


__all__ = ["params_hash", "extract_frame", "make_draft_clip"]
