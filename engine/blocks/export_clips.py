"""Export Clips block (terminal): turn one long video into many short MP4s.

Given a video and a list of :class:`Moments`, writes one MP4 per moment to the output
folder — the "10 shorts from a long video" workflow. Pairs naturally with AI Part
Extraction or Key Moments (highlights mode). Optionally uses an LLM to write a punchy
on-screen hook/title for each clip.

All written paths are returned in ``MediaRef.meta['clips']`` so the worker collects
every clip (see ``RunResult.media_paths``).
"""
from __future__ import annotations

import logging
import os

from engine.block import PREVIEW_CLIP, ParamSpec, PipelineBlock, PortSpec
from engine.blocks._ai import llm_param_specs, llm_text
from engine.blocks._encode import encode_param_specs, resolve_encode, write_video
from engine.blocks.export import write_metadata_package
from engine.clipkit import load_clip
from engine.context import ExecutionContext
from engine.ports import MEDIA, MOMENTS, MediaRef, Moments
from engine.registry import register_block

log = logging.getLogger(__name__)


@register_block
class ExportClipsBlock(PipelineBlock):
    type_id = "export_clips"
    title = "Export Clips"
    category = "output"
    description = "Write one short MP4 per moment (with optional AI hook overlays)."
    preview_kind = PREVIEW_CLIP

    inputs = [
        PortSpec("media", MEDIA),
        PortSpec("moments", MOMENTS),
    ]
    outputs = [PortSpec("video", MEDIA)]
    params = [
        ParamSpec("out_dir", "folder", "", label="Output folder",
                  help="Blank = config output_dir."),
        ParamSpec("prefix", "str", "clip", label="File name prefix"),
        *encode_param_specs(),
        ParamSpec("ai_hook", "bool", False, label="AI hook overlay",
                  help="Burn an LLM-written hook/title onto each clip."),
        ParamSpec("hook_style", "enum", "curiosity", advanced=True,
                  choices=["curiosity", "bold claim", "question", "listicle"],
                  label="Hook style"),
        *llm_param_specs(),
    ]

    # -- helpers ---------------------------------------------------------------
    def _out_dir(self, ctx: ExecutionContext) -> str:
        out_dir = self.p("out_dir", "") or ctx.config.output_dir
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

    def _hook_for(self, ctx, moment) -> str:
        text = (moment.text or "").strip()
        if not text:
            return ""
        style = self.p("hook_style", "curiosity")
        prompt = (
            f"Write a single short on-screen hook (max 8 words, {style} style) for a "
            "vertical short based on this clip transcript. Return ONLY the hook text, "
            "no quotes, no hashtags, no emojis.\n\n" + text
        )
        try:
            return llm_text(ctx, self, prompt).strip().strip('"')
        except Exception as exc:  # hooks are best-effort
            log.warning("AI hook generation failed: %s", exc)
            return ""

    def _overlay_hook(self, ctx, clip, hook: str):
        from moviepy.editor import CompositeVideoClip, TextClip  # type: ignore[import]

        from engine.blocks.subtitles import _configure_imagemagick

        _configure_imagemagick(ctx)
        txt = TextClip(
            hook, fontsize=max(int(clip.w * 0.06), 24), color="white",
            stroke_color="black", stroke_width=2, method="caption", align="center",
            size=(int(clip.w * 0.9), None),
        ).set_duration(clip.duration).set_position(("center", int(clip.h * 0.08)))
        return CompositeVideoClip([clip, txt])

    # -- block API -------------------------------------------------------------
    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        media: MediaRef = inputs["media"]
        moments = inputs.get("moments")
        items = moments.items if isinstance(moments, Moments) else []
        base = load_clip(media)

        if not items:
            raise ValueError("Export Clips needs at least one moment to cut.")

        if ctx.preview:
            return {"video": self._draft_first(ctx, media, base, items[0])}

        out_dir = self._out_dir(ctx)
        prefix = self.p("prefix", "clip") or "clip"
        ai_hook = self.p("ai_hook", False)
        enc = resolve_encode(self, base, ctx.config)
        width = max(len(str(len(items))), 2)
        paths = []
        manifest_paths = []
        metadata_paths = []
        for i, m in enumerate(items, 1):
            ctx.progress(f"Rendering clip {i}/{len(items)}", i / (len(items) + 1))
            sub = base.subclip(max(0.0, m.start), min(base.duration, m.end))
            if ai_hook:
                hook = self._hook_for(ctx, m)
                if hook:
                    sub = self._overlay_hook(ctx, sub, hook)
            out_path = os.path.join(out_dir, f"{prefix}_{i:0{width}d}.mp4")
            write_video(sub, out_path, enc, ctx, tag=f"clip{i}")
            paths.append(out_path)
            package = write_metadata_package(
                ctx,
                media,
                out_path,
                enc,
                transformation_notes=f"Extracted clip {i} of {len(items)} with ViGenX",
                duration=float(sub.duration or 0),
            )
            manifest_paths.append(package["manifest_path"])
            metadata_paths.append(package["metadata_path"])

        ctx.progress("Export clips complete", 1.0)
        first = MediaRef(path=paths[0], duration=None, source_url=media.source_url,
                         title=media.title, meta={
                             "clips": paths,
                             "manifest_paths": manifest_paths,
                             "metadata_paths": metadata_paths,
                         })
        return {"video": first}

    def _draft_first(self, ctx, media, base, moment) -> MediaRef:
        sub = base.subclip(max(0.0, moment.start), min(base.duration, moment.end))
        if sub.duration and sub.duration > 4:
            sub = sub.subclip(0, 4)
        if getattr(sub, "w", 0) and sub.w > 480:
            sub = sub.resize(width=480)
        out_path = ctx.temp_path("clips_draft.mp4")
        sub.write_videofile(
            out_path, codec="libx264", audio_codec="aac", preset="ultrafast",
            ffmpeg_params=["-crf", "28"], temp_audiofile=ctx.temp_path("clips-draft-audio.m4a"),
            remove_temp=True, verbose=False, logger=None,
        )
        return MediaRef(path=out_path, duration=sub.duration, title=media.title)

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        return self.process(ctx, inputs)["video"]
