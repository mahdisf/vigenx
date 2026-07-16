"""Speaker short video pipeline.

Creates under-60-second speaker highlight clips using Whisper transcription,
key-moment scoring, transitions, subtitles, and optional background music.
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import sys
import textwrap
import time
from dataclasses import dataclass
from typing import Optional

from config import AppConfig, load_config
from core.downloader import download_video
from core.logging_setup import configure_logging
from core.manifest import build_default_manifest, save_manifest
from core.metadata import VideoMetadata, save_metadata
from core.transcription import SubtitleSegment, transcribe
from pipelines.base import BasePipeline, PipelineResult

log = logging.getLogger(__name__)


@dataclass
class KeyMoment:
    start: float
    end: float
    text: str
    importance_score: float
    keywords: list[str]


_IMPORTANT_KEYWORDS = [
    "important", "key", "crucial", "remember", "main", "point", "conclusion",
    "summary", "finally", "therefore", "because", "however", "but", "so",
    "first", "second", "third", "next", "also", "additionally", "furthermore",
]


def _score_key_moments(
    segments: list[SubtitleSegment], max_duration: int
) -> list[KeyMoment]:
    moments: list[KeyMoment] = []
    for seg in segments:
        words = seg.text.lower().split()
        score = min(len(words) * 0.1, 2.0)
        score += sum(1.0 for kw in _IMPORTANT_KEYWORDS if kw in seg.text.lower())
        if "?" in seg.text or "!" in seg.text:
            score += 0.5
        if score > 1.0:
            moments.append(
                KeyMoment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    importance_score=score,
                    keywords=[w for w in words if w in _IMPORTANT_KEYWORDS],
                )
            )
    moments.sort(key=lambda m: m.importance_score, reverse=True)

    selected: list[KeyMoment] = []
    total = 0.0
    for m in moments:
        dur = m.end - m.start
        if total + dur <= max_duration - 10:
            selected.append(m)
            total += dur
    return selected


class SpeakerPipeline(BasePipeline):
    def run(
        self,
        *,
        source: str,
        source_type: str = "local",
        output_name: Optional[str] = None,
        blur_faces: bool = False,
        language: Optional[str] = None,
        whisper_model: Optional[str] = None,
        no_music: bool = False,
        **_,
    ) -> PipelineResult:
        from moviepy.audio.fx import all as afx  # type: ignore[import]
        from moviepy.editor import (  # type: ignore[import]
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            TextClip,
            VideoFileClip,
            concatenate_videoclips,
        )

        cfg = self.config
        model_size = whisper_model or cfg.whisper_model

        # 1. Get video
        self._progress("Resolving source", 0.0)
        if source_type == "local":
            video_path = source
            if not os.path.isfile(video_path):
                raise FileNotFoundError(f"Input file not found: {video_path}")
            source_url = None
        else:
            self._progress("Downloading video", 0.05)
            import tempfile
            tmp = tempfile.mkdtemp(prefix="cr_speaker_")
            video_path = download_video(source, tmp)
            source_url = source

        # 2. Transcribe
        self._progress("Transcribing speech", 0.15)
        segments = transcribe(video_path, model_size=model_size, language=language)
        if not segments:
            raise RuntimeError("No speech detected in video")

        # 3. Key moments
        self._progress("Scoring key moments", 0.30)
        key_moments = _score_key_moments(segments, cfg.max_duration)
        if not key_moments:
            raise RuntimeError("No key moments identified")
        log.info("Selected %d key moments", len(key_moments))

        # 4. Create clips
        self._progress("Creating clips", 0.40)
        clips = []
        for i, moment in enumerate(key_moments):
            try:
                clip = VideoFileClip(video_path).subclip(moment.start, moment.end)
                if i == 0:
                    clip = clip.fadein(cfg.fade_duration)
                if i == len(key_moments) - 1:
                    clip = clip.fadeout(cfg.fade_duration)
                clips.append(clip)
            except Exception as exc:
                log.warning("Error creating clip %d: %s", i + 1, exc)
        if not clips:
            raise RuntimeError("Failed to create any video clips")

        # 5. Concatenate
        self._progress("Concatenating clips", 0.55)
        final_video = concatenate_videoclips(clips, method="compose")
        if final_video.duration > cfg.max_duration:
            final_video = final_video.subclip(0, cfg.max_duration)

        # 6. Face blur
        if blur_faces:
            self._progress("Applying face blur", 0.60)
            from core.face_blur import build_face_blur_filter
            final_video = final_video.fl_image(build_face_blur_filter())

        # 7. Background music
        if not no_music and os.path.isdir(cfg.music_folder):
            self._progress("Adding background music", 0.65)
            music_files = [
                f for f in os.listdir(cfg.music_folder)
                if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))
            ]
            if music_files:
                try:
                    mf = os.path.join(cfg.music_folder, random.choice(music_files))
                    with AudioFileClip(mf) as music:
                        if music.duration > final_video.duration:
                            start_t = random.uniform(0, music.duration - final_video.duration)
                            music = music.subclip(start_t, start_t + final_video.duration)
                        elif music.duration < final_video.duration:
                            music = music.fx(afx.audio_loop, duration=final_video.duration)
                        music = music.fx(afx.volumex, cfg.music_volume)
                        if final_video.audio:
                            final_audio = CompositeAudioClip([final_video.audio, music])
                        else:
                            final_audio = music
                        final_video = final_video.set_audio(final_audio)
                except Exception as exc:
                    log.warning("Could not add background music: %s", exc)

        # 8. Subtitles
        self._progress("Adding subtitles", 0.75)
        font_path = os.path.join(cfg.fonts_dir, "Roboto_Condensed-Black.ttf")
        if not os.path.isfile(font_path):
            font_path = None
        subtitle_clips = []
        current_t = 0.0
        for moment in key_moments:
            for line in textwrap.wrap(moment.text, width=30):
                try:
                    sub = (
                        TextClip(
                            line, fontsize=40, color="white", font=font_path,
                            stroke_color="black", stroke_width=2, method="caption",
                        )
                        .set_duration(min(3.0, final_video.duration - current_t))
                        .set_start(current_t)
                        .set_position(("center", "bottom"))
                    )
                    subtitle_clips.append(sub)
                    current_t += 2.5
                except Exception as exc:
                    log.warning("Error creating subtitle: %s", exc)
        if subtitle_clips:
            final_video = CompositeVideoClip([final_video] + subtitle_clips)

        # 9. Export
        self._progress("Exporting video", 0.85)
        out_dir = cfg.speaker_output_dir
        os.makedirs(out_dir, exist_ok=True)
        if output_name is None:
            output_name = f"speaker_short_{int(time.time())}.mp4"
        out_path = os.path.join(out_dir, output_name)

        final_video.write_videofile(
            out_path,
            fps=cfg.output_fps,
            codec=cfg.video_codec,
            audio_codec=cfg.audio_codec,
            preset=cfg.preset,
            ffmpeg_params=["-crf", str(cfg.crf)],
        )
        for c in clips:
            c.close()
        final_video.close()

        # 10. Manifest & metadata
        self._progress("Saving manifest and metadata", 0.95)
        manifest = build_default_manifest(
            output_video_path=out_path,
            source_url=source_url,
            ai_tools=[f"Whisper {model_size}"],
            transformation_notes="Speaker short: key-moment scoring, transitions, subtitles, background music",
        )
        manifest_path = save_manifest(manifest, out_dir)

        meta = VideoMetadata(
            title=output_name,
            description="",
            tags=[],
            pipeline_type="speaker",
            duration_seconds=final_video.duration,
            source_url=source_url,
            render_settings={"codec": cfg.video_codec, "fps": cfg.output_fps, "crf": cfg.crf},
        )
        base_name = os.path.splitext(output_name)[0]
        metadata_path = save_metadata(meta, out_dir, base_name)

        self._progress("Done", 1.0)
        return PipelineResult(
            output_path=out_path,
            manifest_path=manifest_path,
            metadata_path=metadata_path,
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Speaker short video maker")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Path to local video file")
    src.add_argument("--url", help="URL to download")
    p.add_argument("--output", "-o", default=None, help="Output filename")
    p.add_argument("--blur-faces", action="store_true")
    p.add_argument("--language", "-l", default=None)
    p.add_argument("--whisper-model", default="small",
                   choices=["tiny", "base", "small", "medium", "large"])
    p.add_argument("--no-music", action="store_true")
    p.add_argument("--config", default="config/default_config.toml")
    return p


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    cfg = load_config(args.config)
    pipeline = SpeakerPipeline(config=cfg)
    pipeline.run(
        source=args.input or args.url,
        source_type="local" if args.input else "url",
        output_name=args.output,
        blur_faces=args.blur_faces,
        language=args.language,
        whisper_model=args.whisper_model,
        no_music=args.no_music,
    )


if __name__ == "__main__":
    main()
