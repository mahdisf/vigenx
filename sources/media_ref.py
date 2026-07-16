"""Normalized media reference for the source-selection layer.

A :class:`MediaReference` is one selectable item produced by the resolver — a
single local file or a single remote video. The web layer renders these as a
multi-select grid; selected refs are fed into a batch graph run (the ``source``
node's params are overridden per ref).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class MediaReference:
    source_url: str = ""          # remote URL, if any
    local_path: str = ""          # local file path, if already on disk
    title: str = ""
    duration: Optional[float] = None
    thumbnail: str = ""
    status: str = "pending"       # pending | ready | error
    selected: bool = True
    meta: dict = field(default_factory=dict)

    @property
    def source(self) -> str:
        """The value the ``source`` block should receive."""
        return self.local_path or self.source_url

    @property
    def source_type(self) -> str:
        return "local" if self.local_path else "url"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source
        d["source_type"] = self.source_type
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MediaReference":
        return cls(
            source_url=d.get("source_url", "") or (d.get("source", "") if d.get("source_type") == "url" else ""),
            local_path=d.get("local_path", "") or (d.get("source", "") if d.get("source_type") == "local" else ""),
            title=d.get("title", ""),
            duration=d.get("duration"),
            thumbnail=d.get("thumbnail", ""),
            status=d.get("status", "pending"),
            selected=d.get("selected", True),
            meta=dict(d.get("meta") or {}),
        )


__all__ = ["MediaReference"]
