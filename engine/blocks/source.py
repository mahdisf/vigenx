"""Source block: turns a local file or URL into a :class:`MediaRef`.

Wraps :func:`core.downloader.download_video` for URLs and
:func:`core.audio_utils.get_video_duration` for probing. In a batch run the worker
injects the per-item ``source``/``source_type`` via ``param_overrides`` so one graph
serves many selected media items.
"""
from __future__ import annotations

import logging
import os

from engine.block import PipelineBlock, ParamSpec, PortSpec
from engine.context import ExecutionContext
from engine.ports import MEDIA, MediaRef
from engine.registry import register_block

log = logging.getLogger(__name__)


@register_block
class SourceBlock(PipelineBlock):
    type_id = "source"
    title = "Source"
    category = "source"
    description = "Load a base video from a local file or a URL (yt-dlp)."

    inputs = []
    outputs = [PortSpec("media", MEDIA, label="Video")]
    params = [
        ParamSpec("source_type", "enum", "local", choices=["local", "url"],
                  label="Source type"),
        ParamSpec("source", "file", "", label="Source",
                  help="Local file path (Browse) or a video URL."),
        ParamSpec("max_height", "enum", "auto",
                  choices=["auto", "2160", "1440", "1080", "720", "480", "360"],
                  label="Max resolution",
                  help="Max download resolution for URL sources; 'auto' = native/best."),
    ]

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        source = self.p("source", "")
        source_type = self.p("source_type", "local")
        if not source:
            raise ValueError("Source block has no 'source' configured")

        source_url = None
        if source_type == "url":
            from core.downloader import download_video

            ctx.progress("Downloading source", 0.1)
            dl_dir = ctx.subdir("source")
            mh = self.p("max_height", "auto")
            max_height = 9999 if str(mh) == "auto" else int(mh)
            path = download_video(source, dl_dir, max_height=max_height)
            source_url = source
        else:
            path = source
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Source file not found: {path}")

        duration = None
        try:
            from core.audio_utils import get_video_duration

            duration = get_video_duration(path)
        except Exception as exc:  # probing is best-effort
            log.debug("Could not probe duration for %s: %s", path, exc)

        media = MediaRef(
            path=path,
            duration=duration,
            source_url=source_url,
            title=os.path.splitext(os.path.basename(path))[0],
        )
        return {"media": media}
