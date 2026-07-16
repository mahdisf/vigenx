"""AI subtitle cleanup / translation block.

Takes Whisper subtitle segments and rewrites their text with an LLM — fixing
punctuation/casing/obvious transcription errors, or translating to another language —
while preserving each segment's original start/end timings. One structured call returns
the rewritten lines by index, so the captions stay perfectly aligned with the video.
Requires an API key for the chosen provider.
"""
from __future__ import annotations

from engine.block import PREVIEW_NONE, ParamSpec, PipelineBlock, PortSpec
from engine.blocks._ai import llm_param_specs, llm_structured
from engine.context import ExecutionContext
from engine.ports import SUBTITLES, Subtitles
from engine.registry import register_block
from core.transcription import SubtitleSegment

_MODES = {
    "clean": "Fix punctuation, capitalization, and obvious speech-to-text errors. "
             "Keep the original language and meaning. Do not merge or split lines.",
    "translate": "Translate each line into the target language, preserving meaning and "
                 "keeping each line roughly the same length. Do not merge or split lines.",
}


@register_block
class AISubtitlesBlock(PipelineBlock):
    type_id = "ai_subtitles"
    title = "AI Subtitle Fix"
    category = "ai"
    description = "Clean up or translate subtitles with an LLM (timings preserved)."
    preview_kind = PREVIEW_NONE

    inputs = [PortSpec("subtitles", SUBTITLES)]
    outputs = [PortSpec("subtitles", SUBTITLES)]
    params = [
        ParamSpec("mode", "enum", "clean", choices=list(_MODES), label="Mode"),
        ParamSpec("target_language", "str", "English", label="Target language",
                  help="Used when mode is 'translate'."),
        ParamSpec("batch_size", "int", 80, min=10, max=400, advanced=True,
                  label="Lines per request"),
        *llm_param_specs(),
    ]

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        from typing import List

        from pydantic import BaseModel, Field

        subs = inputs.get("subtitles")
        segs = subs.normalized() if isinstance(subs, Subtitles) else []
        if not segs:
            return {"subtitles": Subtitles(segments=[])}

        mode = self.p("mode", "clean")
        instruction = _MODES[mode]
        if mode == "translate":
            instruction += f" Target language: {self.p('target_language', 'English')}."

        class _Line(BaseModel):
            index: int = Field(description="0-based line index from the input")
            text: str = Field(description="rewritten text for this line")

        class _Result(BaseModel):
            lines: List[_Line]

        out: List[SubtitleSegment] = []
        batch = max(self.p("batch_size", 80), 1)
        for offset in range(0, len(segs), batch):
            chunk = segs[offset:offset + batch]
            numbered = "\n".join(f"{i}: {t}" for i, (_, _, t) in enumerate(chunk))
            prompt = (
                f"{instruction}\n\nRewrite each numbered line and return its index and "
                "new text. Return the SAME number of lines, one per input line.\n\n"
                f"{numbered}"
            )
            result = llm_structured(ctx, self, prompt, _Result)
            by_index = {ln.index: ln.text for ln in result.lines}
            for i, (start, end, original) in enumerate(chunk):
                out.append(SubtitleSegment(
                    start=start, end=end, text=by_index.get(i, original).strip()))

        return {"subtitles": Subtitles(segments=out)}
