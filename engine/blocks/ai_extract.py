"""AI part-extraction block: use an LLM to pick the most engaging moments.

Asks the selected provider (Gemini / Groq / NVIDIA via :mod:`core.llm`) to choose the
most viral / keynote / funny segments from the transcript and return them as scored
:class:`Moments`. Produces a *varied-length list* of non-overlapping highlights — ideal
for feeding the multi-clip Export Clips block to turn one long video into many shorts.
Requires an API key for the chosen provider (set in Settings).
"""
from __future__ import annotations

from engine.block import PREVIEW_NONE, ParamSpec, PipelineBlock, PortSpec
from engine.blocks._ai import llm_param_specs, llm_structured
from engine.context import ExecutionContext
from engine.ports import MOMENTS, SUBTITLES, Moment, Moments, Subtitles
from engine.registry import register_block

_MODES = {
    "virality": "the most viral, attention-grabbing, shareable moments",
    "keynote": "the key points, main takeaways, and conclusions",
    "fun": "the funniest and most emotionally engaging moments",
    "topic": "moments that best summarize each distinct topic",
}


@register_block
class AIExtractBlock(PipelineBlock):
    type_id = "ai_extract"
    title = "AI Part Extraction"
    category = "ai"
    description = "Use an LLM to select the best moments (one per future short clip)."
    preview_kind = PREVIEW_NONE

    inputs = [PortSpec("subtitles", SUBTITLES)]
    outputs = [PortSpec("moments", MOMENTS)]
    params = [
        ParamSpec("mode", "enum", "virality", choices=list(_MODES), label="Extraction goal"),
        ParamSpec("count", "int", 10, min=1, max=50, label="Number of moments"),
        ParamSpec("min_clip", "float", 8.0, min=1.0, max=600.0, label="Min clip length (s)"),
        ParamSpec("max_clip", "float", 60.0, min=2.0, max=600.0, label="Max clip length (s)"),
        *llm_param_specs(),
    ]

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        from typing import List

        from pydantic import BaseModel, Field

        subs = inputs.get("subtitles")
        segs = subs.normalized() if isinstance(subs, Subtitles) else []
        if not segs:
            return {"moments": Moments(items=[])}

        count = self.p("count", 10)
        lo = self.p("min_clip", 8.0)
        hi = max(self.p("max_clip", 60.0), lo)

        class _Moment(BaseModel):
            start: float = Field(description="start time in seconds")
            end: float = Field(description="end time in seconds")
            score: float = Field(default=1.0, description="0-1 importance/virality score")
            reason: str = Field(default="", description="short reason this moment was chosen")

        class _Result(BaseModel):
            moments: List[_Moment]

        transcript = "\n".join(f"[{s:.1f}-{e:.1f}] {t}" for s, e, t in segs)
        goal = _MODES[self.p("mode", "virality")]
        prompt = (
            f"Here is a timestamped transcript. Select up to {count} of {goal}. "
            f"Each selected moment must be a self-contained clip between {lo:.0f} and "
            f"{hi:.0f} seconds long, and the moments must NOT overlap. Vary the lengths "
            "naturally. Use ONLY timestamps present in the transcript.\n\n" + transcript
        )
        result = llm_structured(ctx, self, prompt, _Result)

        text_at = {(round(s, 1), round(e, 1)): t for s, e, t in segs}
        candidates = []
        for m in result.moments:
            if m.end <= m.start:
                continue
            # Clamp the model's window into the allowed duration range.
            dur = min(max(m.end - m.start, lo), hi)
            end = m.start + dur
            candidates.append(Moment(
                start=m.start, end=end, score=m.score, label=m.reason,
                text=text_at.get((round(m.start, 1), round(m.end, 1)), ""),
            ))

        # Highest-scoring first, drop overlaps, then restore chronological order.
        candidates.sort(key=lambda m: m.score, reverse=True)
        selected: List[Moment] = []
        for m in candidates:
            if len(selected) >= count:
                break
            if any(m.start < s.end and s.start < m.end for s in selected):
                continue
            selected.append(m)
        selected.sort(key=lambda m: m.start)
        return {"moments": Moments(items=selected)}
