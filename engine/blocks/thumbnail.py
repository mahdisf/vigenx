"""Thumbnail block: extract a cover frame and overlay an optional title bar.

Operates on a rendered video file (typically wired after ``export``), reusing
:func:`core.thumbnail.generate_thumbnail`.
"""
from __future__ import annotations

from engine.block import PREVIEW_NONE, ParamSpec, PipelineBlock, PortSpec
from engine.context import ExecutionContext
from engine.ports import IMAGE, MEDIA, ImageRef
from engine.registry import register_block


@register_block
class ThumbnailBlock(PipelineBlock):
    type_id = "thumbnail"
    title = "Thumbnail"
    category = "output"
    description = "Generate a cover image from a rendered video with an optional title."
    preview_kind = PREVIEW_NONE

    inputs = [PortSpec("video", MEDIA)]
    outputs = [PortSpec("image", IMAGE)]
    params = [
        ParamSpec("timestamp", "float", 5.0, min=0.0, label="Frame time (s)"),
        ParamSpec("title", "str", "", label="Title text"),
        ParamSpec("text_color", "color", "white", advanced=True, label="Text color"),
        ParamSpec("stroke_color", "color", "#FD3C9D", advanced=True, label="Stroke color"),
        ParamSpec("font_path", "file", "", advanced=True, label="Font file"),
    ]

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        from core.thumbnail import generate_thumbnail, thumbnail_path_for

        video = inputs["video"]
        out_path = thumbnail_path_for(video.path)
        result = generate_thumbnail(
            video.path,
            out_path,
            timestamp=self.p("timestamp", 5.0),
            title=self.p("title", ""),
            font_path=self.p("font_path", ""),
            text_color=self.p("text_color", "white"),
            stroke_color=self.p("stroke_color", "#FD3C9D"),
        )
        return {"image": ImageRef(path=result or out_path)}
