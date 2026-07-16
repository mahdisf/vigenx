"""Intro/outro block: concatenate clips around the main video."""
from __future__ import annotations

from engine.block import PREVIEW_CLIP, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import MEDIA
from engine.registry import register_block


@register_block
class IntroOutroBlock(PipelineBlock):
    type_id = "intro_outro"
    title = "Intro / Outro"
    category = "branding"
    description = "Prepend an intro and/or append an outro clip."
    preview_kind = PREVIEW_CLIP

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("intro_clip", "file", "", label="Intro clip"),
        ParamSpec("outro_clip", "file", "", label="Outro clip"),
    ]

    def _apply(self, ctx, media):
        from core.video_utils import prepend_append_clips

        clip = load_clip(media)
        intro = self.p("intro_clip", "") or getattr(ctx.config, "intro_clip", "")
        outro = self.p("outro_clip", "") or getattr(ctx.config, "outro_clip", "")
        out = prepend_append_clips(clip, intro_path=intro, outro_path=outro)
        return derive(media, out)

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        return {"media": self._apply(ctx, inputs["media"])}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        out = self._apply(ctx, inputs["media"])
        return save_frame(out.clip, t, ctx.temp_path("preview_introoutro.jpg"), max_width=720)
