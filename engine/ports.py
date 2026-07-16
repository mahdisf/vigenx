"""Typed data payloads that flow along graph edges.

Ports are identified by short string type constants. The executor passes the
payload object produced by an upstream node's output port to the connected
downstream input port. Edge validation only checks the port *type* string;
``ANY`` is compatible with everything.

Payloads are deliberately lightweight: media payloads carry a filesystem path
plus metadata rather than decoded frames, so passing data between blocks is cheap
and blocks open/close clips themselves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

# --- Port type constants -------------------------------------------------------
MEDIA = "media"          # a video file (MediaRef)
AUDIO = "audio"          # an audio file (AudioRef)
SUBTITLES = "subtitles"  # timed text segments (Subtitles)
MOMENTS = "moments"      # scored time ranges (Moments)
TEXT = "text"            # plain text payload (Text)
IMAGE = "image"          # a still image file (ImageRef)
ANY = "any"              # wildcard, compatible with any other type

PORT_TYPES = (MEDIA, AUDIO, SUBTITLES, MOMENTS, TEXT, IMAGE, ANY)


def types_compatible(producer: str, consumer: str) -> bool:
    """Return True if a value of port type ``producer`` may feed ``consumer``."""
    if producer == ANY or consumer == ANY:
        return True
    return producer == consumer


# --- Payloads ------------------------------------------------------------------
@dataclass
class MediaRef:
    """A reference to a video file plus lightweight metadata.

    ``clip`` optionally holds an in-memory MoviePy clip representing the *current*
    edited state as it flows between blocks; only the export block renders it to
    disk. It is never serialized — templates store the graph, not payloads.
    """

    path: str
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    source_url: Optional[str] = None
    title: Optional[str] = None
    meta: dict = field(default_factory=dict)
    clip: Any = field(default=None, repr=False, compare=False)


@dataclass
class AudioRef:
    path: str
    duration: Optional[float] = None
    sample_rate: Optional[int] = None


@dataclass
class Subtitles:
    """A list of timed text segments.

    ``segments`` holds objects with ``.start``, ``.end`` and ``.text`` (the
    ``SubtitleSegment`` produced by :mod:`core.transcription`), but plain dicts
    with the same keys are also accepted via :meth:`normalized`.
    """

    segments: List[Any] = field(default_factory=list)

    def normalized(self) -> List[Tuple[float, float, str]]:
        out: List[Tuple[float, float, str]] = []
        for s in self.segments:
            if isinstance(s, dict):
                out.append((float(s["start"]), float(s["end"]), str(s["text"])))
            else:
                out.append((float(s.start), float(s.end), str(s.text)))
        return out


@dataclass
class Moment:
    start: float
    end: float
    score: float = 0.0
    label: str = ""
    text: str = ""


@dataclass
class Moments:
    items: List[Moment] = field(default_factory=list)


@dataclass
class Text:
    value: str = ""


@dataclass
class ImageRef:
    path: str
    width: Optional[int] = None
    height: Optional[int] = None


__all__ = [
    "MEDIA",
    "AUDIO",
    "SUBTITLES",
    "MOMENTS",
    "TEXT",
    "IMAGE",
    "ANY",
    "PORT_TYPES",
    "types_compatible",
    "MediaRef",
    "AudioRef",
    "Subtitles",
    "Moment",
    "Moments",
    "Text",
    "ImageRef",
]
