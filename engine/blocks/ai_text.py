"""AI text-generation block: write titles/descriptions/hashtags/hooks from a transcript.

Uses the selected LLM provider (:mod:`core.llm`) to turn the transcript (and optionally
the selected moments) into a piece of text — a title, description, hashtag set, hook
line, or a free-form custom prompt. Emits :class:`Text` so it can feed Narration (TTS),
a future overlay, or metadata. Requires an API key for the chosen provider.
"""
from __future__ import annotations

from engine.block import PREVIEW_NONE, ParamSpec, PipelineBlock, PortSpec
from engine.blocks._ai import llm_param_specs, llm_text
from engine.context import ExecutionContext
from engine.ports import MOMENTS, SUBTITLES, TEXT, Moments, Subtitles, Text
from engine.registry import register_block

_KINDS = {
    "title": "a single punchy video title (max 12 words, no quotes, no hashtags)",
    "description": "a 2-3 sentence video description",
    "hashtags": "8-12 relevant hashtags on one line, space separated",
    "hook": "a 1-line scroll-stopping opening hook (max 12 words)",
    "summary": "a concise summary of the key points",
    "custom": "",  # uses custom_prompt
}


@register_block
class AITextBlock(PipelineBlock):
    type_id = "ai_text"
    title = "AI Text"
    category = "ai"
    description = "Generate a title, description, hashtags, hook, or summary with an LLM."
    preview_kind = PREVIEW_NONE

    inputs = [
        PortSpec("subtitles", SUBTITLES),
        PortSpec("moments", MOMENTS, required=False),
    ]
    outputs = [PortSpec("text", TEXT)]
    params = [
        ParamSpec("kind", "enum", "title", choices=list(_KINDS), label="What to generate"),
        ParamSpec("language", "str", "", label="Language",
                  help="Blank = same language as the transcript."),
        ParamSpec("tone", "str", "", label="Tone",
                  help="e.g. energetic, professional, funny. Blank = neutral."),
        ParamSpec("custom_prompt", "text", "", advanced=True, label="Custom prompt",
                  help="Used when 'What to generate' is 'custom'."),
        *llm_param_specs(),
    ]

    def _transcript(self, inputs: dict) -> str:
        subs = inputs.get("subtitles")
        segs = subs.normalized() if isinstance(subs, Subtitles) else []
        lines = [t for _, _, t in segs]
        moments = inputs.get("moments")
        if isinstance(moments, Moments) and moments.items:
            picked = [m.text for m in moments.items if m.text]
            if picked:
                lines = picked
        return "\n".join(lines).strip()

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        transcript = self._transcript(inputs)
        if not transcript:
            return {"text": Text(value="")}

        kind = self.p("kind", "title")
        if kind == "custom":
            instruction = self.p("custom_prompt", "") or "Summarize this transcript."
        else:
            instruction = f"Write {_KINDS[kind]}."

        extras = []
        if self.p("language", ""):
            extras.append(f"Write it in {self.p('language')}.")
        if self.p("tone", ""):
            extras.append(f"Use a {self.p('tone')} tone.")
        extras.append("Return ONLY the requested text, with no preamble or markdown.")

        prompt = (
            f"{instruction} {' '.join(extras)}\n\n"
            f"Transcript:\n{transcript}"
        )
        value = llm_text(ctx, self, prompt).strip()
        return {"text": Text(value=value)}
