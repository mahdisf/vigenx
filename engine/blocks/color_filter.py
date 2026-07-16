"""Color-filter block: brightness / contrast / saturation. WYSIWYG (frame preview)."""
from __future__ import annotations

from engine.block import PREVIEW_FRAME, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import MEDIA
from engine.registry import register_block


@register_block
class ColorFilterBlock(PipelineBlock):
    type_id = "color_filter"
    title = "Color Filter"
    category = "effects"
    description = "Adjust brightness, contrast, and saturation (1.0 = no change)."
    preview_kind = PREVIEW_FRAME

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("brightness", "float", 1.0, min=0.0, max=3.0, label="Brightness"),
        ParamSpec("contrast", "float", 1.0, min=0.0, max=3.0, label="Contrast"),
        ParamSpec("saturation", "float", 1.1, min=0.0, max=3.0, label="Saturation"),
    ]

    def _apply(self, media):
        from core.video_utils import apply_color_filter

        clip = load_clip(media)
        out = apply_color_filter(
            clip,
            brightness=self.p("brightness", 1.0),
            contrast=self.p("contrast", 1.0),
            saturation=self.p("saturation", 1.1),
        )
        return derive(media, out)

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        return {"media": self._apply(inputs["media"])}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        out = self._apply(inputs["media"])
        return save_frame(out.clip, t, ctx.temp_path("preview_color.jpg"), max_width=720)
