"""Instagram Reels uploader via instagrapi (lazy, graceful).

Uses a saved session from the credential store to publish a clip as a Reel.
Dependencies and credentials are loaded lazily so importing this module never
fails.
"""
from __future__ import annotations

import logging
from typing import Optional

from publishing.uploaders.base import Uploader, UploadRequest, UploadResult

log = logging.getLogger(__name__)


def build_caption(request: UploadRequest) -> str:
    parts = [request.title or "", request.description or ""]
    if request.tags:
        parts.append(" ".join(f"#{tag.lstrip('#')}" for tag in request.tags))
    return "\n\n".join(part for part in parts if part).strip()


class InstagramUploader(Uploader):
    platform = "instagram"

    def _deps(self):
        try:
            from instagrapi import Client  # type: ignore[import]

            return Client
        except ImportError:
            return None

    def _creds_dir(self) -> str:
        return getattr(self.config, "credentials_dir", "credentials") if self.config else "credentials"

    def _session(self) -> Optional[dict]:
        from publishing.credentials import CredentialStore

        return CredentialStore(self._creds_dir()).load("instagram")

    def available(self) -> bool:
        return self._deps() is not None and self._session() is not None

    def unavailable_reason(self) -> str:
        if self._deps() is None:
            return "Install instagrapi"
        if self._session() is None:
            return "No Instagram session in credential store"
        return ""

    def upload(self, request: UploadRequest) -> UploadResult:
        client_class = self._deps()
        session = self._session()
        if not client_class or not session:
            return UploadResult(ok=False, platform=self.platform, error=self.unavailable_reason())
        try:
            client = client_class()
            client.set_settings(session)
            media = client.clip_upload(request.video_path, caption=build_caption(request))
            code = getattr(media, "code", "")
            return UploadResult(
                ok=True,
                platform=self.platform,
                video_id=str(getattr(media, "pk", "")),
                url=f"https://www.instagram.com/reel/{code}/" if code else "",
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("Instagram upload failed")
            return UploadResult(ok=False, platform=self.platform, error=str(exc))


__all__ = ["InstagramUploader", "build_caption"]
