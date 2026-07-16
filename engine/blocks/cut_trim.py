"""Cut / trim block: select a time range and optionally cap the duration."""
from __future__ import annotations

from engine.block import PREVIEW_CLIP, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import MEDIA, MediaRef
from engine.registry import register_block


@register_block
class CutTrimBlock(PipelineBlock):
    type_id = "cut_trim"
    title = "Cut / Trim"
    category = "edit"
    description = "Keep a time range of the video and optionally cap its length."
    preview_kind = PREVIEW_CLIP

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("start", "float", 0.0, min=0.0, label="Start (s)"),
        ParamSpec("end", "float", 0.0, min=0.0, label="End (s)",
                  help="0 = to the end of the clip."),
        ParamSpec("max_duration", "int", 0, min=0, advanced=True,
                  label="Max duration (s)", help="0 = no cap."),
    ]

    def _trim(self, media: MediaRef) -> MediaRef:
        clip = load_clip(media)
        start = max(0.0, self.p("start", 0.0))
        end = self.p("end", 0.0)
        duration = getattr(clip, "duration", None) or 0.0
        end = duration if not end or end > duration else end
        if start > 0.0 or end < duration:
            clip = clip.subclip(start, end)
        cap = self.p("max_duration", 0)
        if cap and clip.duration > cap:
            clip = clip.subclip(0, cap)
        return derive(media, clip)

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        return {"media": self._trim(inputs["media"])}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        out = self._trim(inputs["media"])
        return save_frame(out.clip, t, ctx.temp_path("preview_cut.jpg"), max_width=720)
