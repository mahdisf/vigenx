"""Narration block: synthesize speech from text into an audio track.

Wraps :func:`core.tts.text_to_speech`. Emits an :class:`AudioRef` that a
downstream audio-mix block (e.g. ``background_music``) can lay over the video.
"""
from __future__ import annotations

from engine.block import PREVIEW_NONE, ParamSpec, PipelineBlock, PortSpec
from engine.context import ExecutionContext
from engine.ports import AUDIO, TEXT, AudioRef, Text
from engine.registry import register_block


@register_block
class NarrateTTSBlock(PipelineBlock):
    type_id = "narrate_tts"
    title = "Narration (TTS)"
    category = "audio"
    description = "Convert generated text into a spoken-audio track."
    preview_kind = PREVIEW_NONE

    inputs = [PortSpec("text", TEXT)]
    outputs = [PortSpec("audio", AUDIO)]
    params = [
        ParamSpec("engine", "enum", "pyttsx3", choices=["pyttsx3", "coqui"], label="TTS engine"),
        ParamSpec("model", "str", "tts_models/en/vctk/vits", advanced=True, label="Coqui model"),
        ParamSpec("speaker", "str", "p339", advanced=True, label="Speaker id"),
        ParamSpec("language", "str", "en", advanced=True, label="Language"),
        ParamSpec("speaker_wav", "file", "", advanced=True, label="Voice sample (clone)"),
    ]

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        from core.tts import text_to_speech

        payload = inputs.get("text")
        text = payload.value if isinstance(payload, Text) else str(payload or "")
        out_path = ctx.temp_path("narration.wav")
        text_to_speech(
            text,
            out_path,
            model_name=self.p("model", "tts_models/en/vctk/vits"),
            speaker=self.p("speaker", "p339") or None,
            language=self.p("language", "en") or None,
            speaker_wav=self.p("speaker_wav", "") or None,
            engine=self.p("engine", "pyttsx3"),
        )
        return {"audio": AudioRef(path=out_path)}
