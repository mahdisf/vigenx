"""Browser uploader scaffold for platforms without an open post API.

Playwright and saved storage state are loaded lazily. Site-specific automation
is intentionally not implemented because upload selectors and confirmation
signals must be validated against a live, authorized account.
"""
from __future__ import annotations

import logging
from typing import Optional

from publishing.uploaders.base import Uploader, UploadRequest, UploadResult

log = logging.getLogger(__name__)

_UPLOAD_URLS = {
    "tiktok": "https://www.tiktok.com/upload",
    "playwright": "about:blank",
}

_NOT_IMPLEMENTED = (
    "Playwright upload automation is not implemented; no upload was attempted"
)


class PlaywrightUploader(Uploader):
    def __init__(self, config=None, platform: str = "tiktok") -> None:
        super().__init__(config)
        self.platform = platform

    def _deps(self):
        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import]

            return sync_playwright
        except ImportError:
            return None

    def _creds_dir(self) -> str:
        return getattr(self.config, "credentials_dir", "credentials") if self.config else "credentials"

    def _storage_state(self) -> Optional[dict]:
        from publishing.credentials import CredentialStore

        return CredentialStore(self._creds_dir()).load(self.platform)

    def available(self) -> bool:
        return self._deps() is not None and self._storage_state() is not None

    def unavailable_reason(self) -> str:
        if self._deps() is None:
            return "Install playwright (and run: playwright install)"
        if self._storage_state() is None:
            return f"No {self.platform} cookie/storage-state in credential store"
        return ""

    def upload(self, request: UploadRequest) -> UploadResult:
        sync_playwright = self._deps()
        state = self._storage_state()
        if not sync_playwright or not state:
            return UploadResult(ok=False, platform=self.platform, error=self.unavailable_reason())
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(storage_state=state)
                page = context.new_page()
                page.goto(_UPLOAD_URLS.get(self.platform, "about:blank"))
                # No upload occurs until platform-specific selectors and a
                # successful-post confirmation signal are implemented.
                browser.close()
            return UploadResult(ok=False, platform=self.platform, error=_NOT_IMPLEMENTED)
        except Exception as exc:  # noqa: BLE001
            log.exception("Playwright upload failed")
            return UploadResult(ok=False, platform=self.platform, error=str(exc))


__all__ = ["PlaywrightUploader"]
