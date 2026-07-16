"""Resolve any input into a list of selectable :class:`MediaReference` items.

Handles local files, local folders/globs, and single/playlist URLs. Playlist,
channel, and page enumeration uses yt-dlp's flat extraction when available and
degrades gracefully to a single reference offline. (Full Instagram/channel
enumeration is fleshed out in the Phase 3 sources work.)
"""
from __future__ import annotations

import glob
import logging
import os
from typing import List

from sources.media_ref import MediaReference

log = logging.getLogger(__name__)

_VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv")


def resolve(source: str, source_type: str = "auto", limit: int = 200) -> List[MediaReference]:
    source = (source or "").strip()
    if not source:
        return []
    if source_type == "auto":
        source_type = _detect_type(source)
    if source_type == "local":
        return _resolve_local(source, limit)
    if source_type == "instagram":
        return _resolve_instagram(source, limit)
    # url, playlist, and channel all enumerate through yt-dlp
    return _resolve_url(source, limit)


def _detect_type(source: str) -> str:
    if os.path.exists(source) or any(c in source for c in "*?"):
        return "local"
    if "instagram.com" in source or source.startswith("@"):
        return "instagram"
    return "url"


def _resolve_instagram(source: str, limit: int) -> List[MediaReference]:
    try:
        from sources.instagram import enumerate_profile

        return enumerate_profile(source, limit=limit)
    except Exception as exc:  # missing dep / private / offline
        log.warning("Instagram enumeration failed: %s", exc)
        return [MediaReference(source_url=source, title=source, status="error",
                               meta={"error": str(exc)})]


def _resolve_local(source: str, limit: int) -> List[MediaReference]:
    paths: List[str] = []
    if os.path.isdir(source):
        for name in sorted(os.listdir(source)):
            if name.lower().endswith(_VIDEO_EXTS):
                paths.append(os.path.join(source, name))
    elif any(c in source for c in "*?"):
        paths = sorted(p for p in glob.glob(source) if p.lower().endswith(_VIDEO_EXTS))
    elif os.path.isfile(source):
        paths = [source]
    refs = []
    for p in paths[:limit]:
        refs.append(MediaReference(
            local_path=os.path.abspath(p),
            title=os.path.splitext(os.path.basename(p))[0],
            duration=_safe_duration(p),
            status="ready",
        ))
    return refs


def _resolve_url(source: str, limit: int) -> List[MediaReference]:
    try:
        import yt_dlp  # type: ignore[import]

        opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist",
                "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(source, download=False)
    except Exception as exc:  # offline / single video / unsupported
        log.info("URL enumeration fell back to single ref (%s)", exc)
        return [MediaReference(source_url=source, title=source, status="pending")]

    entries = info.get("entries") if isinstance(info, dict) else None
    if not entries:
        return [MediaReference(
            source_url=info.get("webpage_url", source) if isinstance(info, dict) else source,
            title=(info.get("title") if isinstance(info, dict) else "") or source,
            duration=info.get("duration") if isinstance(info, dict) else None,
            thumbnail=info.get("thumbnail", "") if isinstance(info, dict) else "",
            status="pending",
        )]
    refs = []
    for e in entries[:limit]:
        if not e:
            continue
        url = e.get("url") or e.get("webpage_url") or ""
        if url and not url.startswith("http"):
            url = e.get("webpage_url", url)
        refs.append(MediaReference(
            source_url=url,
            title=e.get("title", "") or url,
            duration=e.get("duration"),
            thumbnail=e.get("thumbnail", ""),
            status="pending",
        ))
    return refs


def _safe_duration(path: str):
    try:
        from core.audio_utils import get_video_duration

        return get_video_duration(path)
    except Exception:
        return None


__all__ = ["resolve"]
