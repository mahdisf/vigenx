"""Silence-trim block: drop silent gaps, keeping only voiced intervals.

Wraps :func:`core.audio_utils.detect_voiced_intervals`. Detection runs on the
*current* clip's audio (rendered to a temp WAV) so it composes correctly after an
upstream cut — no manual time-shifting needed.
"""
from __future__ import annotations

from engine.block import PREVIEW_FRAME, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame, trim_to_voiced
from engine.context import ExecutionContext
from engine.ports import MEDIA
from engine.registry import register_block


@register_block
class SilenceTrimBlock(PipelineBlock):
    type_id = "silence_trim"
    title = "Trim Silence"
    category = "edit"
    description = "Remove silent gaps, keeping only voiced segments."
    preview_kind = PREVIEW_FRAME  # appearance of a single frame is unchanged

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("top_db", "float", 28.0, min=10.0, max=60.0, label="Silence threshold (dB)",
                  help="Higher = more aggressive silence removal."),
        ParamSpec("pad", "float", 0.05, min=0.0, max=1.0, advanced=True,
                  label="Padding (s)", help="Keep this much around each voiced span."),
    ]

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        from core.audio_utils import detect_voiced_intervals

        media = inputs["media"]
        clip = load_clip(media)
        if clip.audio is None:
            return {"media": media}
        wav = ctx.temp_path("silence_probe.wav")
        clip.audio.write_audiofile(wav, fps=16000, nbytes=2, codec="pcm_s16le",
                                   verbose=False, logger=None)
        intervals = detect_voiced_intervals(wav, top_db=self.p("top_db", 28.0))
        if intervals:
            clip = trim_to_voiced(clip, intervals, pad=self.p("pad", 0.05))
        return {"media": derive(media, clip)}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        # Trimming doesn't alter how a single frame looks; show the input frame.
        clip = load_clip(inputs["media"])
        return save_frame(clip, t, ctx.temp_path("preview_silence.jpg"), max_width=720)
