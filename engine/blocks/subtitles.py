"""Subtitle burn-in block.

Composites timed text over the clip. This is a primary WYSIWYG block: its
``preview`` renders a single composited frame so color/position/font changes show
up on the real video within a fraction of a second.

Lifts the overlay construction from ``pipelines/general_pipeline._burn_subtitles``
and exposes its styling as parameters. Requires ImageMagick for ``TextClip`` (path
taken from ``AppConfig.imagemagick_binary``).
"""
from __future__ import annotations

import logging
import os
from typing import Any, List, Tuple

from engine.block import PREVIEW_FRAME, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import MEDIA, SUBTITLES, Subtitles
from engine.registry import register_block

log = logging.getLogger(__name__)

_POSITIONS = ["bottom", "center", "top"]


def _configure_imagemagick(ctx: ExecutionContext) -> None:
    binary = getattr(ctx.config, "imagemagick_binary", "")
    if binary and os.path.isfile(binary):
        try:
            from moviepy.config import change_settings  # type: ignore[import]

            change_settings({"IMAGEMAGICK_BINARY": binary})
        except Exception as exc:  # pragma: no cover
            log.debug("Could not set ImageMagick binary: %s", exc)


@register_block
class SubtitlesBlock(PipelineBlock):
    type_id = "subtitles"
    title = "Subtitles"
    category = "edit"
    description = "Burn timed captions onto the video with configurable styling."
    preview_kind = PREVIEW_FRAME

    inputs = [
        PortSpec("media", MEDIA),
        PortSpec("subtitles", SUBTITLES),
    ]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("font_size", "int", 42, min=8, max=200, label="Font size"),
        ParamSpec("color", "color", "white", label="Text color"),
        ParamSpec("stroke_color", "color", "black", label="Outline color"),
        ParamSpec("font", "font", "", label="Font",
                  help="System font; blank = default."),
        ParamSpec("position", "enum", "bottom", choices=_POSITIONS, label="Position"),
        ParamSpec("align", "enum", "center", choices=["left", "center", "right"],
                  advanced=True, label="Text alignment"),
        ParamSpec("margin_v", "float", 0.12, min=0.0, max=0.5, advanced=True,
                  label="Vertical margin (frac)",
                  help="Distance from the top/bottom edge as a fraction of height."),
        ParamSpec("pos_x_frac", "float", -1.0, min=-1.0, max=1.0, advanced=True,
                  label="Free X (frac)", help="0-1 overrides Position; -1 = off."),
        ParamSpec("pos_y_frac", "float", -1.0, min=-1.0, max=1.0, advanced=True,
                  label="Free Y (frac)", help="0-1 overrides Position; -1 = off."),
        ParamSpec("stroke_width", "int", 2, min=0, max=10, advanced=True, label="Outline width"),
        ParamSpec("width_frac", "float", 0.9, min=0.3, max=1.0, advanced=True,
                  label="Text width fraction"),
        ParamSpec("sample_text", "str", "Sample subtitle text", advanced=True,
                  label="Sample text",
                  help="Shown in the preview when no subtitles are connected."),
    ]

    # -- composition -----------------------------------------------------------
    def _position(self, clip_w: int, clip_h: int) -> Any:
        # Free positioning overrides the preset when both fracs are in [0, 1].
        px, py = self.p("pos_x_frac", -1.0), self.p("pos_y_frac", -1.0)
        if 0.0 <= px <= 1.0 and 0.0 <= py <= 1.0:
            return (int(clip_w * px), int(clip_h * py))
        margin = self.p("margin_v", 0.12)
        pos = self.p("position", "bottom")
        if pos == "top":
            return ("center", int(clip_h * margin))
        if pos == "center":
            return ("center", "center")
        return ("center", clip_h - int(clip_h * margin))

    def _composite(self, ctx: ExecutionContext, clip: Any, segs: List[Tuple[float, float, str]]) -> Any:
        from moviepy.editor import CompositeVideoClip, TextClip  # type: ignore[import]

        _configure_imagemagick(ctx)
        pos = self._position(clip.w, clip.h)
        font = self.p("font", "") or None
        overlays = []
        for start, end, text in segs:
            kwargs = dict(
                fontsize=self.p("font_size", 42),
                color=self.p("color", "white"),
                stroke_color=self.p("stroke_color", "black"),
                stroke_width=self.p("stroke_width", 2),
                method="caption",
                align=self.p("align", "center"),
                size=(int(clip.w * self.p("width_frac", 0.9)), None),
            )
            if font:
                kwargs["font"] = font
            txt = TextClip(text, **kwargs)
            txt = txt.set_start(max(start, 0.0)).set_end(end).set_position(pos)
            overlays.append(txt)
        if not overlays:
            return clip
        return CompositeVideoClip([clip, *overlays])

    def _segments(self, inputs: dict) -> List[Tuple[float, float, str]]:
        subs = inputs.get("subtitles")
        if isinstance(subs, Subtitles):
            return subs.normalized()
        return []

    # -- block API -------------------------------------------------------------
    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        media = inputs["media"]
        clip = load_clip(media)
        composited = self._composite(ctx, clip, self._segments(inputs))
        return {"media": derive(media, composited)}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        media = inputs["media"]
        clip = load_clip(media)
        all_segs = self._segments(inputs)
        # Only render captions near the previewed instant to keep it snappy.
        segs = [s for s in all_segs if s[0] - 1 <= t <= s[1] + 1] or all_segs[:1]
        if not segs:
            # No subtitles wired yet — show the sample text so styling is visible.
            sample = self.p("sample_text", "") or "Sample subtitle text"
            segs = [(max(t - 1.0, 0.0), t + 1.0, sample)]
        composited = self._composite(ctx, clip, segs)
        return save_frame(composited, t, ctx.temp_path("preview_subs.jpg"), max_width=720)
