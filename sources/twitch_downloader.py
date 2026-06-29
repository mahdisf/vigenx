"""Twitch VOD/playlist downloader with sequential naming and download history."""
from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)


def is_video_downloaded(video_id: str, history_file: str) -> bool:
    if not os.path.exists(history_file):
        return False
    with open(history_file, encoding="utf-8") as f:
        return video_id in {line.strip() for line in f}


def log_downloaded_video(video_id: str, history_file: str) -> None:
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"{video_id}\n")


def get_next_video_id(output_dir: str, game_name: str) -> int:
    """Return next sequential ID by scanning existing files."""
    max_id = 0
    if not os.path.isdir(output_dir):
        return 1
    for filename in os.listdir(output_dir):
        if filename.startswith(f"{game_name}-") and filename.endswith(".mp4"):
            base = filename[:-4]
            parts = base.split("-")
            if len(parts) > 1:
                try:
                    vid = int(parts[-1])
                    max_id = max(max_id, vid)
                except ValueError:
                    pass
    return max_id + 1


def get_next_processed_video_id(
    output_dir: str,
    game_name: str,
    Auto: bool = True,
) -> tuple[int | None, str | None]:
    """
    Return (video_id, video_title) for the next video to process.

    Auto=True  — scans *_processed.mp4 files and returns the next sequential ID.
    Auto=False — reads selected_videos.txt (format: ID,"title") and returns the
                 first entry that does not yet have a *_processed.mp4 file.
    """
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    if Auto:
        max_id = 0
        for filename in os.listdir(output_dir):
            if filename.startswith(f"{game_name}-") and filename.endswith("_processed.mp4"):
                base = filename[:-14]  # strip _processed.mp4
                parts = base.split("-")
                if len(parts) > 1:
                    try:
                        vid = int(parts[-1])
                        max_id = max(max_id, vid)
                    except ValueError:
                        pass
        return max_id + 1, None

    # Manual mode
    selection_file = os.path.join(output_dir, "selected_videos.txt")
    if not os.path.isfile(selection_file):
        log.error("'selected_videos.txt' not found in '%s'. Cannot proceed in manual mode.", output_dir)
        return None, None

    with open(selection_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                id_str, title_part = line.split(",", 1)
                vid = int(id_str.strip())
                title = title_part.strip()
                processed = f"{game_name}-{vid}_processed.mp4"
                if not os.path.isfile(os.path.join(output_dir, processed)):
                    return vid, title
            except (ValueError, IndexError):
                log.warning("Malformed line in selected_videos.txt: %s", line)

    log.info("All videos in selected_videos.txt have been processed.")
    return None, None


def get_video_entries(url: str) -> list[dict]:
    import yt_dlp  # noqa: PLC0415 — heavy dep, lazy-loaded
    log.info("Fetching video/playlist metadata from %s …", url)
    try:
        ydl_opts = {"quiet": True, "extract_flat": "in_playlist"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if "entries" in info:
            log.info("Playlist with %d videos", len(info["entries"]))
            return list(info["entries"])
        return [info]
    except Exception as exc:
        log.error("Could not fetch video info: %s", exc)
        return []


def _download_single_video(url: str, output_path: str, game_name: str = "", quiet: bool = True) -> bool:
    import yt_dlp  # noqa: PLC0415
    ydl_opts = {
        "format": "best",
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "quiet": quiet,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as exc:
        log.error("Download failed for %s: %s", url, exc)
        return False


def download_twitch_vod(
    url: str,
    output_dir: str,
    game_name: str,
    quiet: bool = False,
) -> list[str]:
    """Download new videos from a Twitch URL, skip already-downloaded ones."""
    os.makedirs(output_dir, exist_ok=True)
    history_file = os.path.join(output_dir, "download_history.txt")
    entries = get_video_entries(url)
    if not entries:
        return []

    downloaded: list[str] = []
    for i, entry in enumerate(entries, 1):
        twitch_id = entry.get("id")
        entry_url = entry.get("url")
        title = entry.get("title", "Untitled")
        log.info("[%d/%d] %s (ID: %s)", i, len(entries), title, twitch_id)

        if is_video_downloaded(twitch_id, history_file):
            log.info("Already downloaded — skipping")
            continue

        next_id = get_next_video_id(output_dir, game_name)
        out_path = os.path.join(output_dir, f"{game_name}-{next_id}.mp4")
        if _download_single_video(entry_url, out_path, quiet=quiet):
            log_downloaded_video(twitch_id, history_file)
            downloaded.append(out_path)
            log.info("Saved as %s", out_path)
        else:
            log.warning("Failed to download: %s", title)

    return downloaded


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m sources.twitch_downloader <URL> [game_name]")
        sys.exit(1)
    from core.logging_setup import configure_logging
    configure_logging()
    _url = sys.argv[1]
    _game = sys.argv[2] if len(sys.argv) > 2 else "Counter-Strike"
    download_twitch_vod(_url, "downloads", _game)
