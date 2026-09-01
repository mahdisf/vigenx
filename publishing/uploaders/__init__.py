"""Upload targets. Resolve one by platform name via :func:`get_uploader`."""
from __future__ import annotations

from publishing.uploaders.base import Uploader, UploadResult


def get_uploader(platform: str, config=None) -> Uploader:
    platform = (platform or "folder").lower()
    if platform == "folder":
        from publishing.uploaders.folder import FolderUploader

        return FolderUploader(config)
    if platform == "youtube":
        from publishing.uploaders.youtube import YouTubeUploader

        return YouTubeUploader(config)
    if platform == "instagram":
        from publishing.uploaders.instagram import InstagramUploader

        return InstagramUploader(config)
    if platform in ("tiktok", "playwright"):
        from publishing.uploaders.playwright import PlaywrightUploader

        return PlaywrightUploader(config, platform=platform)
    raise ValueError(f"Unknown upload platform: {platform!r}")


def uploader_status(config=None, platforms=("folder", "youtube", "instagram", "tiktok")) -> list:
    """Return availability info for each platform (for the UI)."""
    out = []
    for platform in platforms:
        try:
            uploader = get_uploader(platform, config)
            out.append(
                {
                    "platform": platform,
                    "available": uploader.available(),
                    "reason": uploader.unavailable_reason(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            out.append({"platform": platform, "available": False, "reason": str(exc)})
    return out


__all__ = ["get_uploader", "uploader_status", "Uploader", "UploadResult"]
