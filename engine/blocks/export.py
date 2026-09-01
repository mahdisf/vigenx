"""Export block (terminal): render the clip to MP4 plus a metadata package.

Writes the final video and, alongside it, a rights manifest, metadata JSON, and a
history row — reusing :mod:`core.manifest`, :mod:`core.metadata`, and
:mod:`core.history`. In preview/draft mode it renders a short, low-res, ultrafast
clip and skips the metadata package.
"""
from __future__ import annotations

import logging
import os
import time

from engine.block import PREVIEW_CLIP, ParamSpec, PipelineBlock, PortSpec
from engine.blocks._encode import encode_param_specs, resolve_encode, write_video
from engine.clipkit import load_clip
from engine.context import ExecutionContext
from engine.ports import MEDIA, MediaRef
from engine.registry import register_block

log = logging.getLogger(__name__)


def write_metadata_package(
    ctx,
    media: MediaRef,
    out_path: str,
    enc,
    *,
    transformation_notes: str,
    duration: float | None = None,
) -> dict:
    """Write rights/metadata sidecars and return their paths."""
    from core.history import append_history_row
    from core.manifest import build_default_manifest, save_manifest
    from core.metadata import VideoMetadata, save_metadata

    out_dir = os.path.dirname(out_path)
    base = os.path.splitext(os.path.basename(out_path))[0]
    manifest = build_default_manifest(
        output_video_path=out_path,
        source_url=media.source_url,
        source_title=media.title,
        transformation_notes=transformation_notes,
    )
    manifest_path = save_manifest(manifest, out_dir)
    meta = VideoMetadata(
        title=media.title or base,
        description="",
        tags=[],
        pipeline_type="graph",
        duration_seconds=float(duration if duration is not None else (media.duration or 0)),
        source_url=media.source_url,
        source_title=media.title,
        render_settings={
            "codec": enc.codec,
            "fps": enc.fps,
            "crf": enc.crf,
            "preset": enc.preset,
        },
    )
    metadata_path = save_metadata(meta, out_dir, base)
    try:
        append_history_row(
            ctx.config.history_csv,
            pipeline="graph",
            title=media.title or base,
            source=media.source_url or media.path,
            output_path=out_path,
            manifest_path=manifest_path,
            metadata_path=metadata_path,
            status="awaiting_review",
        )
    except Exception as exc:  # history is best-effort
        log.debug("History append failed: %s", exc)
    return {"manifest_path": manifest_path, "metadata_path": metadata_path}


@register_block
class ExportBlock(PipelineBlock):
    type_id = "export"
    title = "Export MP4"
    category = "output"
    description = "Render the final video and write its rights/metadata package."
    preview_kind = PREVIEW_CLIP

    inputs = [PortSpec("media", MEDIA)]
    outputs = [PortSpec("video", MEDIA)]
    params = [
        ParamSpec("out_dir", "folder", "", label="Output folder",
                  help="Blank = config output_dir."),
        ParamSpec("filename", "str", "", label="File name",
                  help="Blank = auto (vigenx_<timestamp>.mp4)."),
        *encode_param_specs(),
        ParamSpec("transformation_notes", "text", "Edited with ViGenX pipeline",
                  advanced=True, label="Transformation notes (rights)"),
    ]

    def _out_path(self, ctx: ExecutionContext) -> str:
        out_dir = self.p("out_dir", "") or ctx.config.output_dir
        os.makedirs(out_dir, exist_ok=True)
        name = self.p("filename", "") or f"vigenx_{int(time.time())}.mp4"
        if not name.lower().endswith(".mp4"):
            name += ".mp4"
        return os.path.join(out_dir, name)

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        media: MediaRef = inputs["media"]
        clip = load_clip(media)

        if ctx.preview:
            return {"video": self._render_draft(ctx, media, clip)}

        out_path = self._out_path(ctx)
        enc = resolve_encode(self, clip, ctx.config)

        ctx.progress("Rendering MP4", 0.1)
        write_video(clip, out_path, enc, ctx, tag="export")
        ctx.progress("Writing metadata package", 0.85)
        package = write_metadata_package(
            ctx,
            media,
            out_path,
            enc,
            transformation_notes=self.p("transformation_notes", ""),
            duration=clip.duration,
        )
        ctx.progress("Export complete", 1.0)
        return {"video": MediaRef(path=out_path, duration=clip.duration,
                                  source_url=media.source_url, title=media.title,
                                  meta=package)}

    # -- helpers ---------------------------------------------------------------
    def _render_draft(self, ctx: ExecutionContext, media: MediaRef, clip) -> MediaRef:
        draft_clip = clip
        if clip.duration and clip.duration > 4:
            draft_clip = clip.subclip(0, 4)
        if getattr(clip, "w", 0) and clip.w > 480:
            draft_clip = draft_clip.resize(width=480)
        out_path = ctx.temp_path("draft.mp4")
        draft_clip.write_videofile(
            out_path, codec="libx264", audio_codec="aac", preset="ultrafast",
            ffmpeg_params=["-crf", "28"], temp_audiofile=ctx.temp_path("draft-audio.m4a"),
            remove_temp=True, verbose=False, logger=None,
        )
        return MediaRef(path=out_path, duration=draft_clip.duration, title=media.title)

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        # Draft render of the whole upstream graph.
        media = inputs["media"]
        clip = load_clip(media)
        return self._render_draft(ctx, media, clip)


__all__ = ["ExportBlock", "write_metadata_package"]
