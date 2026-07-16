"""Assembly block: concatenate the selected moments into one clip.

Takes a video plus a :class:`Moments` list and stitches the corresponding
subclips together (with fade in/out on the ends and an optional duration cap),
reproducing the clip-assembly stage of the speaker pipeline.
"""
from __future__ import annotations

from engine.block import PREVIEW_CLIP, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import MEDIA, MOMENTS, Moments
from engine.registry import register_block


@register_block
class MomentsCutBlock(PipelineBlock):
    type_id = "moments_cut"
    title = "Assemble Moments"
    category = "edit"
    description = "Concatenate the selected highlight moments into one clip."
    preview_kind = PREVIEW_CLIP

    inputs = [
        PortSpec("media", MEDIA),
        PortSpec("moments", MOMENTS),
    ]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("fade", "float", 0.5, min=0.0, max=3.0, label="Fade in/out (s)"),
        ParamSpec("max_duration", "int", 59, min=0, max=600, label="Max duration (s)",
                  help="0 = no cap."),
    ]

    def _assemble(self, media, moments):
        from moviepy.editor import concatenate_videoclips  # type: ignore[import]

        base = load_clip(media)
        items = moments.items if isinstance(moments, Moments) else []
        if not items:
            return media
        fade = self.p("fade", 0.5)
        subclips = []
        for i, m in enumerate(items):
            sub = base.subclip(max(0.0, m.start), min(base.duration, m.end))
            if fade > 0 and i == 0:
                sub = sub.fadein(fade)
            if fade > 0 and i == len(items) - 1:
                sub = sub.fadeout(fade)
            subclips.append(sub)
        out = concatenate_videoclips(subclips, method="compose")
        cap = self.p("max_duration", 59)
        if cap and out.duration > cap:
            out = out.subclip(0, cap)
        return derive(media, out)

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        return {"media": self._assemble(inputs["media"], inputs.get("moments"))}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        out = self._assemble(inputs["media"], inputs.get("moments"))
        clip = load_clip(out)
        return save_frame(clip, t, ctx.temp_path("preview_moments.jpg"), max_width=720)
