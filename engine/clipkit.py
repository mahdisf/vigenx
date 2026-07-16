"""Shared MoviePy helpers for video-transform blocks.

Blocks pass an in-memory clip along :class:`MediaRef.clip`; these helpers open a
clip from disk when one isn't attached yet, render a single frame for WYSIWYG
previews (cheap — MoviePy is lazy, so ``get_frame(t)`` renders only that frame),
and apply common edits lifted from the legacy pipelines.

All MoviePy imports are local so importing a block module stays lightweight.
"""
from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple

from engine.ports import ImageRef, MediaRef


def load_clip(media: MediaRef) -> Any:
    """Return the in-memory clip for ``media``, opening it from disk if needed."""
    if media is None:
        raise ValueError(
            "No video input — connect a Source block upstream and set its file/URL."
        )
    if getattr(media, "clip", None) is not None:
        return media.clip
    path = getattr(media, "path", "") or ""
    if not path or not os.path.isfile(path):
        raise ValueError(
            f"Source video not found: {path or '(empty)'}. "
            "Set the Source block's file path or URL."
        )
    from moviepy.editor import VideoFileClip  # type: ignore[import]

    clip = VideoFileClip(path)
    media.clip = clip
    return clip


def derive(media: MediaRef, clip: Any) -> MediaRef:
    """A new MediaRef carrying ``clip`` while preserving source provenance."""
    return MediaRef(
        path=media.path,
        duration=getattr(clip, "duration", media.duration),
        width=getattr(clip, "w", media.width),
        height=getattr(clip, "h", media.height),
        fps=getattr(clip, "fps", media.fps),
        source_url=media.source_url,
        title=media.title,
        meta=dict(media.meta),
        clip=clip,
    )


def save_frame(clip: Any, t: float, out_path: str, max_width: Optional[int] = None) -> ImageRef:
    """Render the frame at time ``t`` to a JPEG and return an :class:`ImageRef`."""
    import numpy as np  # noqa: F401  (ensures numpy is present for moviepy)
    from PIL import Image  # type: ignore[import]

    if clip is None:
        raise ValueError("No frame to preview — the upstream block produced no video.")
    duration = getattr(clip, "duration", None)
    if duration:
        t = max(0.0, min(t, max(0.0, duration - 0.05)))
    frame = clip.get_frame(t)  # HxWx3 uint8 RGB
    img = Image.fromarray(frame)
    if max_width and img.width > max_width:
        h = int(img.height * max_width / img.width)
        img = img.resize((max_width, h))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path, "JPEG", quality=85)
    return ImageRef(path=out_path, width=img.width, height=img.height)


def trim_to_voiced(clip: Any, intervals: List[Tuple[float, float]], pad: float = 0.05) -> Any:
    """Concatenate only the voiced ``intervals`` of ``clip`` (silence removal)."""
    from moviepy.editor import concatenate_videoclips  # type: ignore[import]

    subclips = []
    for s, e in intervals:
        s2 = max(0.0, s - pad)
        e2 = min(clip.duration, e + pad)
        if e2 > s2:
            subclips.append(clip.subclip(s2, e2))
    if not subclips:
        return clip
    return concatenate_videoclips(subclips, method="compose")


def close_clip(clip: Any) -> None:
    try:
        clip.close()
    except Exception:
        pass


__all__ = ["load_clip", "derive", "save_frame", "trim_to_voiced", "close_clip"]
