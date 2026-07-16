"""Key-moment scoring block: rank subtitle segments into highlight moments.

Lifts the heuristic scorer from ``pipelines/speaker_pipeline._score_key_moments``
(keyword hits, length, question/exclamation emphasis) and exposes it as a block.
"""
from __future__ import annotations

from engine.block import PREVIEW_NONE, ParamSpec, PipelineBlock, PortSpec
from engine.context import ExecutionContext
from engine.ports import MOMENTS, SUBTITLES, Moment, Moments, Subtitles
from engine.registry import register_block

_IMPORTANT_KEYWORDS = [
    "important", "key", "crucial", "remember", "main", "point", "conclusion",
    "summary", "finally", "therefore", "because", "however", "but", "so",
    "first", "second", "third", "next", "also", "additionally", "furthermore",
]


def _seg_score(seg) -> float:
    """Heuristic importance score for a ``(start, end, text)`` segment."""
    _, _, text = seg
    low = text.lower()
    words = low.split()
    score = min(len(words) * 0.1, 2.0)
    score += sum(1.0 for kw in _IMPORTANT_KEYWORDS if kw in low)
    if "?" in text or "!" in text:
        score += 0.5
    return score


@register_block
class KeyMomentsBlock(PipelineBlock):
    type_id = "key_moments"
    title = "Key Moments"
    category = "ai"
    description = "Score and select the most important speech segments."
    preview_kind = PREVIEW_NONE

    inputs = [PortSpec("subtitles", SUBTITLES)]
    outputs = [PortSpec("moments", MOMENTS)]
    params = [
        ParamSpec("mode", "enum", "reel", choices=["reel", "highlights"], label="Mode",
                  help="'reel' = one combined highlight; 'highlights' = a list of "
                       "separate clips (for Export Clips)."),
        ParamSpec("max_duration", "int", 59, min=5, max=600, label="Target max duration (s)",
                  help="Total budget for 'reel' mode."),
        ParamSpec("count", "int", 10, min=1, max=50, label="Number of clips",
                  help="'highlights' mode: how many separate moments to produce."),
        ParamSpec("min_clip", "float", 8.0, min=1.0, max=600.0, label="Min clip length (s)",
                  help="'highlights' mode."),
        ParamSpec("max_clip", "float", 60.0, min=2.0, max=600.0, label="Max clip length (s)",
                  help="'highlights' mode."),
        ParamSpec("min_score", "float", 1.0, min=0.0, max=5.0, advanced=True,
                  label="Min score to keep"),
        ParamSpec("headroom", "float", 10.0, min=0.0, max=60.0, advanced=True,
                  label="Duration headroom (s)"),
    ]

    def _score(self, segs):
        """Score each segment; keep those above ``min_score``."""
        min_score = self.p("min_score", 1.0)
        scored = []
        for start, end, text in segs:
            score = _seg_score((start, end, text))
            if score > min_score:
                kws = [w for w in text.lower().split() if w in _IMPORTANT_KEYWORDS]
                scored.append(Moment(start=start, end=end, score=score,
                                     label=",".join(kws), text=text))
        return scored

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        subs = inputs.get("subtitles")
        segs = subs.normalized() if isinstance(subs, Subtitles) else []

        if self.p("mode", "reel") == "highlights":
            return {"moments": Moments(items=self._highlights(segs))}

        # reel: pack the highest-scoring segments under one duration budget.
        scored = self._score(segs)
        scored.sort(key=lambda m: m.score, reverse=True)
        budget = self.p("max_duration", 59) - self.p("headroom", 10.0)
        selected, total = [], 0.0
        for m in scored:
            dur = m.end - m.start
            if total + dur <= budget:
                selected.append(m)
                total += dur
        selected.sort(key=lambda m: m.start)  # chronological for assembly
        return {"moments": Moments(items=selected)}

    def _highlights(self, segs):
        """Build N separate, non-overlapping, varied-length clips around peaks."""
        lo = self.p("min_clip", 8.0)
        hi = max(self.p("max_clip", 60.0), lo)
        count = self.p("count", 10)
        # Index segments so we can grow a window of consecutive lines around a peak.
        order = sorted(range(len(segs)), key=lambda i: _seg_score(segs[i]), reverse=True)
        used = [False] * len(segs)
        windows = []
        for i in order:
            if len(windows) >= count or used[i]:
                continue
            start_i = end_i = i
            s0, e0, _ = segs[i]
            start_t, end_t = s0, e0
            # Grow outward (prefer the higher-scoring neighbour) until >= lo, <= hi.
            while end_t - start_t < lo:
                left_ok = start_i > 0 and not used[start_i - 1]
                right_ok = end_i < len(segs) - 1 and not used[end_i + 1]
                if not left_ok and not right_ok:
                    break
                grow_left = left_ok and (not right_ok or
                                         _seg_score(segs[start_i - 1]) >= _seg_score(segs[end_i + 1]))
                cand_start = segs[start_i - 1][0] if grow_left else start_t
                cand_end = end_t if grow_left else segs[end_i + 1][1]
                if cand_end - cand_start > hi:
                    break
                if grow_left:
                    start_i -= 1; start_t = cand_start
                else:
                    end_i += 1; end_t = cand_end
            for j in range(start_i, end_i + 1):
                used[j] = True
            text = " ".join(segs[j][2] for j in range(start_i, end_i + 1)).strip()
            score = sum(_seg_score(segs[j]) for j in range(start_i, end_i + 1))
            windows.append(Moment(start=start_t, end=min(end_t, start_t + hi),
                                  score=score, text=text))
        windows.sort(key=lambda m: m.start)
        return windows
