"""Logo-overlay block: composite a PNG logo. WYSIWYG (frame preview)."""
from __future__ import annotations

from engine.block import PREVIEW_FRAME, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import MEDIA
from engine.registry import register_block

_POSITIONS = ["top-left", "top-right", "bottom-left", "bottom-right"]


@register_block
class LogoBlock(PipelineBlock):
    type_id = "logo"
    title = "Logo Overlay"
    category = "branding"
    description = "Composite a PNG logo/watermark onto the video."
    preview_kind = PREVIEW_FRAME

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("logo_path", "file", "", label="Logo PNG",
                  help="Path to a PNG with transparency."),
        ParamSpec("position", "enum", "top-right", choices=_POSITIONS, label="Position"),
        ParamSpec("opacity", "float", 0.85, min=0.0, max=1.0, label="Opacity"),
        ParamSpec("scale", "float", 0.10, min=0.01, max=1.0, advanced=True,
                  label="Scale (fraction of width)"),
    ]

    def _apply(self, ctx, media):
        from core.video_utils import add_logo_overlay

        clip = load_clip(media)
        logo_path = self.p("logo_path", "") or getattr(ctx.config, "logo_path", "")
        out = add_logo_overlay(
            clip, logo_path,
            position=self.p("position", "top-right"),
            opacity=self.p("opacity", 0.85),
            scale=self.p("scale", 0.10),
        )
        return derive(media, out)

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        return {"media": self._apply(ctx, inputs["media"])}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        out = self._apply(ctx, inputs["media"])
        return save_frame(out.clip, t, ctx.temp_path("preview_logo.jpg"), max_width=720)
