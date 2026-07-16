"""General-purpose video editor pipeline.

Supports: local file or URL input, Whisper subtitles, silence trimming,
scene detection, face blur, and MP4 export.
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import tempfile
from typing import Optional

from config import AppConfig, load_config
from core.audio_utils import detect_voiced_intervals, get_video_duration
from core.downloader import download_video
from core.face_blur import build_face_blur_filter
from core.logging_setup import configure_logging
from core.manifest import build_default_manifest, save_manifest
from core.metadata import VideoMetadata, save_metadata
from core.transcription import SubtitleSegment, transcribe
from pipelines.base import BasePipeline, PipelineResult

log = logging.getLogger(__name__)


def _burn_subtitles(clip, segments: list[SubtitleSegment], font_size: int = 42):
    from moviepy.editor import CompositeVideoClip, TextClip  # type: ignore[import]

    overlays = []
    for seg in segments:
        txt = TextClip(
            seg.text,
            fontsize=font_size,
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            align="center",
            size=(int(clip.w * 0.9), None),
        )
        txt = txt.set_start(max(seg.start, 0)).set_end(seg.end)
        txt = txt.set_position(("center", clip.h - int(clip.h * 0.15)))
        overlays.append(txt)
    return CompositeVideoClip([clip, *overlays])


def _trim_to_voiced(clip, intervals: list[tuple[float, float]], pad: float = 0.05):
    from moviepy.editor import concatenate_videoclips  # type: ignore[import]

    subclips = []
    for s, e in intervals:
        s2 = max(0, s - pad)
        e2 = min(clip.duration, e + pad)
        if e2 > s2:
            subclips.append(clip.subclip(s2, e2))
    if not subclips:
        return clip
    return concatenate_videoclips(subclips, method="compose")


class GeneralPipeline(BasePipeline):
    def run(
        self,
        *,
        source: str,
        source_type: str = "local",
        out_path: Optional[str] = None,
        whisper: bool = False,
        whisper_model: Optional[str] = None,
        language: Optional[str] = None,
        trim_silence: bool = False,
        silence_top_db: float = 28.0,
        silence_pad: float = 0.05,
        blur_faces: bool = False,
        blur_ksize: int = 61,
        blur_expand: float = 0.35,
        start: float = 0.0,
        end: Optional[float] = None,
        fps: Optional[int] = None,
        crf: Optional[int] = None,
        preset: Optional[str] = None,
        audio_bitrate: str = "192k",
        **_,
    ) -> PipelineResult:
        from moviepy.editor import VideoFileClip  # type: ignore[import]

        cfg = self.config
        tmp = tempfile.mkdtemp(prefix="cr_general_")

        # 1. Resolve input
        self._progress("Resolving source", 0.0)
        if source_type == "local":
            in_path = source
            if not os.path.isfile(in_path):
                raise FileNotFoundError(f"Input file not found: {in_path}")
            source_url = None
        else:
            self._progress("Downloading video", 0.05)
            in_path = download_video(source, tmp)
            source_url = source
        log.info("Input: %s", in_path)

        duration = get_video_duration(in_path)
        clip_start = max(0.0, start)
        clip_end = min(end if end is not None else duration, duration)

        # 2. Load clip
        self._progress("Loading clip", 0.15)
        clip = VideoFileClip(in_path).subclip(clip_start, clip_end)

        # 3. Face blur
        if blur_faces:
            self._progress("Applying face blur", 0.25)
            processor = build_face_blur_filter(blur_ksize, blur_expand)
            clip = clip.fl_image(processor)

        # 4. Silence trimming
        if trim_silence:
            self._progress("Trimming silence", 0.35)
            audio_tmp = os.path.join(tmp, "audio.wav")
            subprocess.check_call(
                ["ffmpeg", "-y", "-i", in_path, "-vn", "-ac", "1", "-ar", "16000", audio_tmp],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            intervals = detect_voiced_intervals(audio_tmp, top_db=silence_top_db)
            if intervals:
                shifted = [
                    (max(0.0, s - clip_start), max(0.0, e - clip_start))
                    for s, e in intervals
                    if e > clip_start and s < clip_end
                ]
                clip = _trim_to_voiced(clip, shifted, pad=silence_pad)

        # 5. Whisper subtitles
        segments: list[SubtitleSegment] = []
        if whisper:
            self._progress("Transcribing with Whisper", 0.50)
            region_path = os.path.join(tmp, "region.mp4")
            subprocess.check_call(
                ["ffmpeg", "-y", "-ss", str(clip_start), "-to", str(clip_end),
                 "-i", in_path, "-c", "copy", region_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            segments = transcribe(region_path, model_size=whisper_model or cfg.whisper_model, language=language)
            if segments:
                self._progress("Burning subtitles", 0.65)
                clip = _burn_subtitles(clip, segments)

        # 6. Export
        self._progress("Exporting video", 0.75)
        os.makedirs(cfg.output_dir, exist_ok=True)
        if out_path is None:
            import time
            out_path = os.path.join(cfg.output_dir, f"general_{int(time.time())}.mp4")

        export_fps = fps or getattr(clip, "fps", None) or cfg.output_fps
        codec = cfg.video_codec
        clip.write_videofile(
            out_path,
            codec=codec,
            audio_codec=cfg.audio_codec,
            audio_bitrate=audio_bitrate,
            temp_audiofile=os.path.join(tmp, "temp-audio.m4a"),
            remove_temp=True,
            threads=os.cpu_count(),
            fps=export_fps,
            preset=preset or cfg.preset,
            ffmpeg_params=["-crf", str(crf or cfg.crf)],
        )
        clip.close()

        # 7. Manifest & metadata
        self._progress("Saving manifest and metadata", 0.90)
        manifest = build_default_manifest(
            output_video_path=out_path,
            source_url=source_url,
            ai_tools=[f"Whisper {cfg.whisper_model}"] if whisper else [],
            transformation_notes="General editing: silence trim, face blur, subtitles",
        )
        manifest_path = save_manifest(manifest, cfg.output_dir)

        meta = VideoMetadata(
            title=os.path.basename(out_path),
            description="",
            tags=[],
            pipeline_type="general",
            duration_seconds=clip_end - clip_start,
            source_url=source_url,
            render_settings={"codec": codec, "fps": export_fps, "crf": crf or cfg.crf},
        )
        base_name = os.path.splitext(os.path.basename(out_path))[0]
        metadata_path = save_metadata(meta, cfg.output_dir, base_name)

        self._progress("Done", 1.0)
        return PipelineResult(
            output_path=out_path,
            manifest_path=manifest_path,
            metadata_path=metadata_path,
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="General-purpose AI video editor")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Path to local video file")
    src.add_argument("--url", help="URL to download (yt-dlp)")
    p.add_argument("--out", default=None, help="Output MP4 path")
    p.add_argument("--whisper", action="store_true", help="Transcribe and burn subtitles")
    p.add_argument("--whisper-model", default="small", choices=["tiny", "base", "small", "medium", "large"])
    p.add_argument("--language", default=None)
    p.add_argument("--trim-silence", action="store_true")
    p.add_argument("--silence-topdb", type=float, default=28.0)
    p.add_argument("--silence-pad", type=float, default=0.05)
    p.add_argument("--blur-faces", action="store_true")
    p.add_argument("--blur-ksize", type=int, default=61)
    p.add_argument("--blur-expand", type=float, default=0.35)
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--end", type=float, default=None)
    p.add_argument("--fps", type=int, default=None)
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--preset", default="medium")
    p.add_argument("--audio-bitrate", default="192k")
    p.add_argument("--config", default="config/default_config.toml")
    return p


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    cfg = load_config(args.config)
    pipeline = GeneralPipeline(config=cfg)
    pipeline.run(
        source=args.input or args.url,
        source_type="local" if args.input else "url",
        out_path=args.out,
        whisper=args.whisper,
        whisper_model=args.whisper_model,
        language=args.language,
        trim_silence=args.trim_silence,
        silence_top_db=args.silence_topdb,
        silence_pad=args.silence_pad,
        blur_faces=args.blur_faces,
        blur_ksize=args.blur_ksize,
        blur_expand=args.blur_expand,
        start=args.start,
        end=args.end,
        fps=args.fps,
        crf=args.crf,
        preset=args.preset,
        audio_bitrate=args.audio_bitrate,
    )


if __name__ == "__main__":
    main()
