"""Transcription block: Whisper speech-to-text -> timed subtitle segments.

Wraps :func:`core.transcription.transcribe`. Transcribes the *current* clip's
audio so segment timings align with whatever upstream edits produced.
"""
from __future__ import annotations

from engine.block import PREVIEW_NONE, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import load_clip
from engine.context import ExecutionContext
from engine.ports import MEDIA, SUBTITLES, Subtitles
from engine.registry import register_block

_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
# Common Whisper language codes (auto = detect). Kept short but covers the usual set.
_LANGUAGES = [
    "auto", "en", "es", "fr", "de", "it", "pt", "nl", "ru", "uk", "pl", "tr",
    "ar", "fa", "he", "hi", "ur", "bn", "id", "vi", "th", "ja", "ko", "zh",
]


@register_block
class TranscribeBlock(PipelineBlock):
    type_id = "transcribe"
    title = "Transcribe (Whisper)"
    category = "ai"
    description = "Generate timed subtitle segments from speech with Whisper."
    preview_kind = PREVIEW_NONE

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("subtitles", SUBTITLES)]
    params = [
        ParamSpec("model", "enum", "small", choices=_WHISPER_MODELS, label="Model size"),
        ParamSpec("language", "enum", "auto", choices=_LANGUAGES, label="Language",
                  help="Spoken language; 'auto' = detect."),
        ParamSpec("task", "enum", "transcribe", choices=["transcribe", "translate"],
                  advanced=True, label="Task",
                  help="'translate' renders the speech as English text."),
        ParamSpec("word_timestamps", "bool", False, advanced=True,
                  label="Word-level timestamps"),
        ParamSpec("temperature", "float", 0.0, min=0.0, max=1.0, advanced=True,
                  label="Temperature"),
        ParamSpec("beam_size", "int", 0, min=0, max=10, advanced=True,
                  label="Beam size", help="0 = Whisper default."),
        ParamSpec("best_of", "int", 0, min=0, max=10, advanced=True,
                  label="Best of", help="0 = Whisper default."),
        ParamSpec("no_speech_threshold", "float", 0.6, min=0.0, max=1.0, advanced=True,
                  label="No-speech threshold"),
        ParamSpec("condition_on_previous_text", "bool", True, advanced=True,
                  label="Condition on previous text"),
        ParamSpec("initial_prompt", "text", "", advanced=True, label="Initial prompt",
                  help="Optional hint/context to bias transcription."),
    ]

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        from core.transcription import transcribe

        media = inputs["media"]
        clip = load_clip(media)
        # Preview/draft mode: cap to a short window so transcription stays fast.
        target = media.path
        if clip.audio is not None:
            wav = ctx.temp_path("transcribe.wav")
            src = clip
            if ctx.preview and clip.duration and clip.duration > 8:
                src = clip.subclip(0, 8)
            src.audio.write_audiofile(wav, fps=16000, nbytes=2, codec="pcm_s16le",
                                      verbose=False, logger=None)
            target = wav
        model = "tiny" if ctx.preview else self.p("model", "small")
        lang = self.p("language", "auto")
        beam = self.p("beam_size", 0)
        best = self.p("best_of", 0)
        segments = transcribe(
            target,
            model_size=model,
            language=None if lang in ("", "auto") else lang,
            word_timestamps=self.p("word_timestamps", False),
            task=self.p("task", "transcribe"),
            temperature=self.p("temperature", 0.0),
            beam_size=beam or None,
            best_of=best or None,
            no_speech_threshold=self.p("no_speech_threshold", 0.6),
            condition_on_previous_text=self.p("condition_on_previous_text", True),
            initial_prompt=self.p("initial_prompt", "") or None,
        )
        return {"subtitles": Subtitles(segments=segments)}
