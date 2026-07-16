"""Vertical-format block: reframe a landscape video to 9:16 (e.g. 1080x1920).

Three modes, none requiring extra ML deps:
  * ``crop``  — scale to cover then center-crop (fills the frame, may lose edges).
  * ``fit``   — letterbox onto a black background (keeps the whole frame).
  * ``blur``  — fit the video centered over a blurred, zoomed copy of itself.

WYSIWYG: ``preview`` renders one reframed frame.
"""
from __future__ import annotations

from engine.block import PREVIEW_FRAME, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import MEDIA
from engine.registry import register_block

_MODES = ["crop", "fit", "blur"]


@register_block
class VerticalCropBlock(PipelineBlock):
    type_id = "vertical_crop"
    title = "Vertical Format"
    category = "effects"
    description = "Reframe to a vertical 9:16 short (crop, letterbox, or blurred fit)."
    preview_kind = PREVIEW_FRAME

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("mode", "enum", "crop", choices=_MODES, label="Reframe mode"),
        ParamSpec("width", "int", 1080, min=240, max=2160, advanced=True, label="Target width"),
        ParamSpec("height", "int", 1920, min=240, max=3840, advanced=True, label="Target height"),
        ParamSpec("blur_strength", "int", 25, min=1, max=99, advanced=True, label="Background blur"),
    ]

    def _reframe(self, media):
        from moviepy.editor import CompositeVideoClip, ColorClip  # type: ignore[import]
        from moviepy.video.fx.all import crop as fx_crop  # type: ignore[import]

        clip = load_clip(media)
        W, H = self.p("width", 1080), self.p("height", 1920)
        mode = self.p("mode", "crop")

        if mode == "crop":
            scale = max(W / clip.w, H / clip.h)
            scaled = clip.resize(scale)
            out = fx_crop(scaled, width=W, height=H,
                          x_center=scaled.w / 2, y_center=scaled.h / 2)
        else:
            fit = min(W / clip.w, H / clip.h)
            fg = clip.resize(fit)
            if mode == "blur":
                cover = max(W / clip.w, H / clip.h)
                bg = fx_crop(clip.resize(cover), width=W, height=H,
                             x_center=clip.resize(cover).w / 2,
                             y_center=clip.resize(cover).h / 2)
                bg = bg.fl_image(self._blur_fn())
            else:  # fit
                bg = ColorClip((W, H), color=(0, 0, 0)).set_duration(clip.duration)
            out = CompositeVideoClip([bg, fg.set_position("center")], size=(W, H))
            out = out.set_duration(clip.duration)

        if clip.audio is not None:
            out = out.set_audio(clip.audio)
        return derive(media, out)

    def _blur_fn(self):
        import cv2

        k = self.p("blur_strength", 25)
        k = k if k % 2 == 1 else k + 1

        def _f(frame):
            dark = (frame * 0.6).astype("uint8")
            return cv2.GaussianBlur(dark, (k, k), 0)

        return _f

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        return {"media": self._reframe(inputs["media"])}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        out = self._reframe(inputs["media"])
        return save_frame(out.clip, t, ctx.temp_path("preview_vertical.jpg"), max_width=540)
