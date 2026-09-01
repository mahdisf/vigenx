"""Folder uploader: publish into the dated render tree. Always available."""
from __future__ import annotations

from publishing.folder_publisher import publish_to_folder
from publishing.uploaders.base import Uploader, UploadRequest, UploadResult


class FolderUploader(Uploader):
    platform = "folder"

    def available(self) -> bool:
        return True

    def upload(self, request: UploadRequest) -> UploadResult:
        renders_dir = getattr(self.config, "renders_dir", "renders") if self.config else "renders"
        try:
            dest = publish_to_folder(request.video_path, renders_dir=renders_dir)
            return UploadResult(ok=True, platform=self.platform, url=dest, video_id=dest)
        except Exception as exc:  # noqa: BLE001
            return UploadResult(ok=False, platform=self.platform, error=str(exc))
