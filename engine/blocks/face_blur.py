"""Face-blur block: blur detected faces frame-by-frame.

Wraps :func:`core.face_blur.build_face_blur_filter`. A WYSIWYG block: ``preview``
shows a single blurred frame so the blur strength/expansion is visible at a glance.
"""
from __future__ import annotations

from engine.block import PREVIEW_FRAME, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import MEDIA
from engine.registry import register_block


@register_block
class FaceBlurBlock(PipelineBlock):
    type_id = "face_blur"
    title = "Face Blur"
    category = "edit"
    description = "Detect and blur faces for privacy."
    preview_kind = PREVIEW_FRAME

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("ksize", "int", 61, min=3, max=199, label="Blur strength",
                  help="Gaussian kernel size (forced odd)."),
        ParamSpec("expand", "float", 0.35, min=0.0, max=1.0, advanced=True,
                  label="Box expansion"),
        ParamSpec("min_confidence", "float", 0.5, min=0.1, max=1.0, advanced=True,
                  label="Min detection confidence"),
    ]

    def _apply(self, media):
        from core.face_blur import build_face_blur_filter

        clip = load_clip(media)
        processor = build_face_blur_filter(
            blur_ksize=self.p("ksize", 61),
            expand=self.p("expand", 0.35),
            min_confidence=self.p("min_confidence", 0.5),
        )
        return derive(media, clip.fl_image(processor))

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        return {"media": self._apply(inputs["media"])}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        out = self._apply(inputs["media"])
        return save_frame(out.clip, t, ctx.temp_path("preview_blur.jpg"), max_width=720)
