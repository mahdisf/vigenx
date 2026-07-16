"""Vocal-separation block: split audio into vocals and instrumental via Demucs.

Wraps :func:`core.vocal_separator.separate_vocals_with_demucs`. Extracts the
clip's audio to WAV, runs Demucs, and emits the two stems as :class:`AudioRef`s.
"""
from __future__ import annotations

from engine.block import PREVIEW_NONE, PipelineBlock, PortSpec
from engine.clipkit import load_clip
from engine.context import ExecutionContext
from engine.ports import AUDIO, MEDIA, AudioRef
from engine.registry import register_block


@register_block
class VocalSeparationBlock(PipelineBlock):
    type_id = "vocal_separation"
    title = "Vocal Separation"
    category = "audio"
    description = "Separate vocals from instrumental audio (Demucs)."
    preview_kind = PREVIEW_NONE

    inputs = [PortSpec("media", MEDIA)]
    outputs = [
        PortSpec("vocals", AUDIO),
        PortSpec("instrumental", AUDIO),
    ]
    params = []

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        from core.audio_utils import extract_audio_wav
        from core.vocal_separator import separate_vocals_with_demucs

        media = inputs["media"]
        clip = load_clip(media)
        wav = ctx.temp_path("demucs_input.wav")
        if clip.audio is not None:
            clip.audio.write_audiofile(wav, fps=44100, nbytes=2, codec="pcm_s16le",
                                       verbose=False, logger=None)
        else:
            extract_audio_wav(media.path, wav, sample_rate=44100)

        result = separate_vocals_with_demucs(wav, ctx.subdir("demucs"))
        if "error" in result:
            raise RuntimeError(f"Vocal separation failed: {result['error']}")
        return {
            "vocals": AudioRef(path=result["vocals"]),
            "instrumental": AudioRef(path=result["no_vocals"]),
        }
