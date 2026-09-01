"""Uploader base class and result types."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List


@dataclass
class UploadResult:
    ok: bool
    platform: str = ""
    url: str = ""
    video_id: str = ""
    error: str = ""


@dataclass
class UploadRequest:
    video_path: str
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    privacy: str = "private"  # private | unlisted | public
    extra: dict = field(default_factory=dict)


class Uploader(abc.ABC):
    platform: str = ""

    def __init__(self, config=None) -> None:
        self.config = config

    @abc.abstractmethod
    def available(self) -> bool:
        """True when required dependencies and credentials are present."""

    def unavailable_reason(self) -> str:
        return "" if self.available() else "dependencies or credentials missing"

    @abc.abstractmethod
    def upload(self, request: UploadRequest) -> UploadResult:
        ...


__all__ = ["Uploader", "UploadRequest", "UploadResult"]
