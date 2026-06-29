from __future__ import annotations

import logging
import os

import yt_dlp

log = logging.getLogger(__name__)


def download_video(
    url: str,
    out_dir: str,
    use_cookies: bool = True,
    max_height: int = 720,
) -> str:
    """
    Download a video via yt-dlp and return the local file path.

    Tries Chrome cookies first, then Firefox, then no cookies as a fallback.
    """
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(title).200s.%(ext)s")

    base_opts: dict = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "merge_output_format": "mp4",
        "format": f"bv*[height<={max_height}]+ba/b[height<={max_height}]/best",
        "quiet": True,
        "no_warnings": True,
    }

    cookie_attempts: list[dict] = []
    if use_cookies:
        for browser in ("chrome", "firefox", "edge"):
            cookie_attempts.append({"cookiesfrombrowser": (browser,)})
    cookie_attempts.append({})  # no-cookie fallback

    last_exc: Exception | None = None
    for extra in cookie_attempts:
        opts = {**base_opts, **extra}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if "_filename" in info:
                    return info["_filename"]
                title = info.get("title", "video")
                ext = info.get("ext", "mp4")
                return os.path.join(out_dir, f"{title}.{ext}")
        except Exception as exc:
            log.warning("Download attempt failed (%s): %s", extra, exc)
            last_exc = exc

    raise RuntimeError(f"Failed to download {url} after all attempts: {last_exc}")
