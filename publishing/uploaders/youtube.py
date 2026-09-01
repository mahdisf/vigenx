"""YouTube Data API v3 uploader using OAuth.

Uploads default to private visibility. Dependencies and OAuth credentials load
lazily, so this module remains safe to import without optional packages.
"""
from __future__ import annotations

import logging
from typing import Optional

from publishing.uploaders.base import Uploader, UploadRequest, UploadResult

log = logging.getLogger(__name__)

_PRIVACY = {"private", "unlisted", "public"}


def build_request_body(request: UploadRequest, category_id: str = "22") -> dict:
    """Build the videos().insert body without making a network request."""
    privacy = request.privacy if request.privacy in _PRIVACY else "private"
    return {
        "snippet": {
            "title": (request.title or "Untitled")[:100],
            "description": request.description or "",
            "tags": request.tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }


class YouTubeUploader(Uploader):
    platform = "youtube"

    def _deps(self):
        try:
            from google.oauth2.credentials import Credentials  # type: ignore[import]
            from googleapiclient.discovery import build  # type: ignore[import]
            from googleapiclient.http import MediaFileUpload  # type: ignore[import]

            return build, MediaFileUpload, Credentials
        except ImportError:
            return None

    def _creds_dir(self) -> str:
        return getattr(self.config, "credentials_dir", "credentials") if self.config else "credentials"

    def _token(self) -> Optional[dict]:
        from publishing.credentials import CredentialStore

        return CredentialStore(self._creds_dir()).load("youtube")

    def available(self) -> bool:
        return self._deps() is not None and self._token() is not None

    def unavailable_reason(self) -> str:
        if self._deps() is None:
            return "Install google-api-python-client + google-auth-oauthlib"
        if self._token() is None:
            return "No YouTube OAuth token in credential store"
        return ""

    def upload(self, request: UploadRequest) -> UploadResult:
        deps = self._deps()
        token = self._token()
        if not deps or not token:
            return UploadResult(ok=False, platform=self.platform, error=self.unavailable_reason())
        build, media_file_upload, credentials = deps
        try:
            creds = credentials.from_authorized_user_info(token)
            youtube = build("youtube", "v3", credentials=creds)
            media = media_file_upload(request.video_path, chunksize=-1, resumable=True)
            req = youtube.videos().insert(
                part="snippet,status",
                body=build_request_body(request),
                media_body=media,
            )
            response = self._resumable_upload(req)
            video_id = response.get("id", "")
            return UploadResult(
                ok=True,
                platform=self.platform,
                video_id=video_id,
                url=f"https://youtu.be/{video_id}" if video_id else "",
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("YouTube upload failed")
            return UploadResult(ok=False, platform=self.platform, error=str(exc))

    @staticmethod
    def _resumable_upload(req, max_retries: int = 3):
        import time

        response = None
        retry = 0
        while response is None:
            try:
                _status, response = req.next_chunk()
            except Exception:
                retry += 1
                if retry > max_retries:
                    raise
                time.sleep(2**retry)
        return response


__all__ = ["YouTubeUploader", "build_request_body"]
