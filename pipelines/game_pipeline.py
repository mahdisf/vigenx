"""Game highlight short video pipeline.

Creates vertical-format gaming highlights with YOLO-based crop,
Demucs vocal separation, Gemini commentary (strict JSON), TTS voiceover,
and stylised overlays.
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import shutil
import tempfile
import textwrap
from typing import Optional

from pydantic import BaseModel

from config import AppConfig, load_config
from core.audio_utils import get_video_duration
from core.gemini_client import generate_structured
from core.history import append_history_row
from core.logging_setup import configure_logging
from core.manifest import build_default_manifest, save_manifest
from core.metadata import VideoMetadata, save_metadata
from core.thumbnail import generate_thumbnail, thumbnail_path_for
from core.tts import text_to_speech
from core.video_utils import add_logo_overlay, apply_color_filter, prepend_append_clips
from core.vocal_separator import separate_vocals_with_demucs
from pipelines.base import BasePipeline, PipelineResult

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schema for Gemini commentary — enforces strict JSON output
# ---------------------------------------------------------------------------

class GameCommentarySchema(BaseModel):
    intro_voice: str
    headline: str
    headline_emoji: str
    title: str
    discription: str  # intentional spelling preserved from original prompt


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class GameHighlightPipeline(BasePipeline):
    def run(
        self,
        *,
        game_name: Optional[str] = None,
        video_id: Optional[int] = None,
        video_title: Optional[str] = None,
        source: str = "",
        source_type: str = "local",
        input_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        music_folder: Optional[str] = None,
        auto_mode: bool = True,
        **_,
    ) -> PipelineResult:
        from moviepy.audio.fx import all as afx  # type: ignore[import]
        from moviepy.editor import (  # type: ignore[import]
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            ImageClip,
            TextClip,
            VideoFileClip,
            concatenate_videoclips,
        )
        from moviepy.config import change_settings  # type: ignore[import]
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]
        from pydub import AudioSegment  # type: ignore[import]

        cfg = self.config
        game = game_name or cfg.game_name
        in_dir = input_dir or cfg.input_dir
        out_dir = output_dir or cfg.output_dir
        music_dir = music_folder or cfg.music_folder

        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # Configure ImageMagick for MoviePy text rendering
        change_settings({"IMAGEMAGICK_BINARY": cfg.imagemagick_binary})

        # Resolve source video path
        self._progress("Resolving source video", 0.00)
        if source and source_type == "url":
            self._progress("Downloading from Twitch/URL", 0.02)
            from sources.twitch_downloader import download_twitch_vod, _download_single_video
            try:
                download_twitch_vod(source, in_dir, game_name=game, quiet=False)
            except Exception:
                _download_single_video(source, in_dir, game_name=game, quiet=False)

        # Determine video_id if not provided
        if video_id is None:
            from sources.twitch_downloader import get_next_processed_video_id
            video_id, video_title = get_next_processed_video_id(out_dir, game, Auto=auto_mode)
            if video_id is None:
                raise RuntimeError("No unprocessed video found. Check selected_videos.txt or input directory.")

        input_video = os.path.join(in_dir, f"{game}-{video_id}.mp4")
        output_video = os.path.join(out_dir, f"{game}-{video_id}_processed.mp4")
        video_title = video_title or ""

        if not os.path.isfile(input_video):
            raise FileNotFoundError(f"Input video not found: {input_video}")

        log.info("Processing: %s → %s", input_video, output_video)

        tmp = tempfile.mkdtemp(prefix="cr_game_")
        demucs_dir: Optional[str] = None

        try:
            # 1. Load and trim to 59 s
            self._progress("Loading video", 0.05)
            video = VideoFileClip(input_video)
            if video.duration > 59:
                start_t = (video.duration - 59) / 2
                video = video.subclip(start_t, start_t + 59)

            # 2. Vocal separation via Demucs
            self._progress("Separating vocals", 0.10)
            instrumental_audio = None
            if video.audio:
                demucs_dir = tempfile.mkdtemp()
                orig_audio_path = os.path.join(demucs_dir, "original_audio.wav")
                video.audio.write_audiofile(orig_audio_path, codec="pcm_s16le", fps=44100, logger=None)
                result = separate_vocals_with_demucs(orig_audio_path, demucs_dir)
                if "error" in result:
                    log.warning("Vocal separation failed: %s — removing audio", result["error"])
                    video = video.without_audio()
                else:
                    instrumental_audio = AudioFileClip(result["no_vocals"])
            else:
                video = video.without_audio()

            # 3. Mix audio: instrumental + background music
            self._progress("Mixing audio", 0.20)
            audio_sources = []
            if instrumental_audio:
                audio_sources.append(instrumental_audio.fx(afx.volumex, 0.7))

            music_file = self._get_random_music(music_dir)
            if music_file:
                music = AudioFileClip(music_file)
                if music.duration > video.duration:
                    st = random.uniform(0, music.duration - video.duration)
                    music = music.subclip(st, st + video.duration)
                elif music.duration < video.duration:
                    music = music.fx(afx.audio_loop, duration=video.duration)
                audio_sources.append(music.fx(afx.volumex, 0.1))

            if audio_sources:
                video = video.set_audio(CompositeAudioClip(audio_sources))
            else:
                video = video.without_audio()

            # 4. Crop to vertical (center 3/4 strip by default; YOLO optional)
            self._progress("Cropping to vertical", 0.30)
            crop_coords = self._get_crop_coords(input_video, cfg)
            audio_track = video.audio
            video = video.crop(
                x1=crop_coords[0], y1=crop_coords[1],
                x2=crop_coords[2], y2=crop_coords[3],
            )
            if audio_track:
                video = video.set_audio(audio_track)

            # 4b. Color filters (brightness / contrast / saturation)
            if cfg.brightness != 1.0 or cfg.contrast != 1.0 or cfg.saturation != 1.0:
                self._progress("Applying color filters", 0.32)
                video = apply_color_filter(video, cfg.brightness, cfg.contrast, cfg.saturation)

            # 5. Gemini commentary (strict JSON)
            self._progress("Generating AI commentary", 0.45)
            duration = get_video_duration(input_video)
            commentary = self._get_commentary(duration, video_title, cfg)
            comment = commentary.headline
            emoji = commentary.headline_emoji
            comment_text = commentary.intro_voice
            title = commentary.title
            description = commentary.discription

            # Save title/description text file
            self._save_details(out_dir, game, video_id, title, description)

            # 6. TTS voiceover
            self._progress("Generating TTS voiceover", 0.55)
            tts_path = os.path.join(tmp, "voiceover.wav")
            tts_duration = 0.0
            try:
                text_to_speech(text=comment_text, file_path=tts_path, engine=cfg.tts_engine)
                tts_audio = AudioFileClip(tts_path, fps=44100)
                delayed_tts = tts_audio.fx(afx.volumex, cfg.voice_volume).set_start(1.5)
                if video.audio:
                    final_audio = CompositeAudioClip([video.audio, delayed_tts])
                else:
                    final_audio = CompositeAudioClip([delayed_tts])
                final_audio = final_audio.fx(afx.volumex, 0.9)
                norm_path = os.path.join(tmp, "norm_audio.wav")
                final_audio.write_audiofile(norm_path, codec="pcm_s16le", fps=44100, logger=None)
                final_audio = AudioFileClip(norm_path).fx(afx.audio_normalize)
                video = video.set_audio(final_audio)
                tts_duration = AudioSegment.from_file(tts_path).duration_seconds
            except Exception as exc:
                log.warning("TTS failed: %s — no voiceover", exc)
                tts_path = None

            # 7. Text overlays
            self._progress("Adding text overlays", 0.65)
            top_text = self._create_text_clip(
                comment, emoji, min(duration, video.duration), fontsize=90, cfg=cfg
            )
            bottom_text = None
            if tts_path and os.path.isfile(tts_path):
                bottom_text = self._create_subtitle_clips(
                    comment_text, tts_path, fontsize=90, cfg=cfg
                )

            # 8. Compose vertical format
            self._progress("Composing vertical format", 0.75)
            background = video.resize(height=1920)
            background = background.crop(
                x_center=background.w / 2,
                y_center=background.h / 2,
                width=1080,
                height=1920,
            )
            background = background.fl_image(lambda f: cv2.GaussianBlur(f, (25, 25), 0))
            video = video.resize(width=1080)

            layers = [background, video.set_position("center"), top_text.set_position(("center", 200))]
            if bottom_text is not None:
                layers.append(bottom_text.set_start(1.5).set_position(("center", 1400)))

            final_video = CompositeVideoClip(layers)
            final_video = final_video.fadein(0.5).fadeout(2.0)
            if video.audio:
                final_video = final_video.fx(afx.audio_fadein, 0.5)
                final_video = final_video.fx(afx.audio_fadeout, 2.0)

            # 8b. Logo overlay
            if cfg.logo_path:
                self._progress("Adding logo overlay", 0.77)
                final_video = add_logo_overlay(
                    final_video, cfg.logo_path,
                    cfg.logo_position, cfg.logo_opacity, cfg.logo_scale,
                )

            # 8c. Intro / outro clips
            if cfg.intro_clip or cfg.outro_clip:
                self._progress("Prepending/appending intro-outro", 0.79)
                final_video = prepend_append_clips(final_video, cfg.intro_clip, cfg.outro_clip)

            # 9. Export
            self._progress("Exporting video", 0.85)
            codec = "h264_nvenc" if cfg.use_gpu_encoder else cfg.video_codec
            ffmpeg_params = ["-rc:v", "vbr", "-cq:v", "18"] if cfg.use_gpu_encoder else ["-crf", str(cfg.crf)]
            final_video.write_videofile(
                output_video,
                fps=cfg.output_fps,
                codec=codec,
                audio_codec=cfg.audio_codec,
                preset=cfg.preset,
                ffmpeg_params=ffmpeg_params,
            )
            video.close()
            final_video.close()

        finally:
            if tts_path and os.path.isfile(tts_path):
                try:
                    os.remove(tts_path)
                except OSError:
                    pass
            if demucs_dir and os.path.isdir(demucs_dir):
                shutil.rmtree(demucs_dir, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)

        # 10. Manifest & metadata
        self._progress("Saving manifest and metadata", 0.95)
        ai_tools = [f"Gemini {cfg.gemini_text_model}", cfg.tts_engine]
        if instrumental_audio:
            ai_tools.append("Demucs mdx_extra_q")
        manifest = build_default_manifest(
            output_video_path=output_video,
            source_title=video_title,
            ai_tools=ai_tools,
            transformation_notes=(
                "Game highlight: vocal separation, vertical crop, Gemini commentary, "
                "TTS voiceover, blurred background, text overlays"
            ),
        )
        manifest_path = save_manifest(manifest, out_dir)

        meta = VideoMetadata(
            title=title,
            description=description,
            tags=[game],
            pipeline_type="game",
            duration_seconds=59.0,
            source_title=video_title,
            render_settings={"codec": codec, "fps": cfg.output_fps, "crf": cfg.crf},
        )
        metadata_path = save_metadata(meta, out_dir, f"{game}-{video_id}_processed")

        # 11. Automated thumbnail / cover
        self._progress("Generating thumbnail", 0.97)
        thumb_path = thumbnail_path_for(output_video)
        generate_thumbnail(
            output_video, thumb_path,
            timestamp=5.0,
            title=title,
            font_path=os.path.join(cfg.fonts_dir, "Roboto_Condensed-Black.ttf"),
            text_color=cfg.text_color,
            stroke_color=cfg.text_stroke_color,
        )

        # 12. History CSV
        append_history_row(
            cfg.history_csv,
            pipeline="game",
            game=game,
            video_id=str(video_id),
            title=title,
            output_path=output_video,
            manifest_path=manifest_path,
            metadata_path=metadata_path,
            status="done",
        )

        self._progress("Done", 1.0)
        return PipelineResult(
            output_path=output_video,
            manifest_path=manifest_path,
            metadata_path=metadata_path,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_random_music(self, music_dir: str) -> Optional[str]:
        if not os.path.isdir(music_dir):
            return None
        files = [f for f in os.listdir(music_dir) if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))]
        return os.path.join(music_dir, random.choice(files)) if files else None

    def _get_crop_coords(self, video_path: str, cfg: AppConfig) -> tuple[int, int, int, int]:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return (560, 0, 1360, 1080)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        left = int(w * 0.25)
        right = int(w * 0.75)
        return (left, 0, right, h)

    def _get_commentary(
        self, duration: float, title: str, cfg: AppConfig
    ) -> GameCommentarySchema:
        voice_secs = int(duration) // 3
        prompt = f"""Analyze this {game} gaming highlight clip and generate short-form video content.
The clip title hint is: "{title}"
Spoken intro must be under {voice_secs} seconds. No markdown, *, /, bold, or hashtags.

Return ONLY a JSON object with these exact fields:
- intro_voice: short spoken intro (~{voice_secs}s) — hype the moment from a viewer's perspective, e.g. "I cannot believe what just happened in this clip"
- headline: 2-word on-screen text capturing the key moment
- headline_emoji: 2-3 relevant emojis
- title: viewer-reaction style title, max 7 words with emojis — phrase it as OTHER people praising the play, e.g. "Nobody Saw That Coming 😱", "How Is That Even Legal 🤯", "The Cleanest Clutch Ever 🔥"
- discription: engaging video description + CTA: bit.ly/3Kb33oE"""

        try:
            return generate_structured(
                prompt,
                GameCommentarySchema,
                model_name=cfg.gemini_text_model,
                api_key=cfg.google_api_key or None,
            )
        except Exception as exc:
            log.warning("Gemini commentary failed: %s — using fallback", exc)
            fallback_comments = [
                "Epic fail!", "So random!", "Mind blown!", "Pure gold!", "Absolutely crazy!"
            ]
            fallback_emojis = ["🤯🎯🔥", "😂🤦💀", "👑🏆🥇", "😱‼️💥", "🤪🍌🤣"]
            return GameCommentarySchema(
                intro_voice=random.choice(fallback_comments),
                headline=random.choice(fallback_comments).split()[0],
                headline_emoji=random.choice(fallback_emojis),
                title=title or "Gaming Highlight",
                discription="Check out this clip! Subscribe: bit.ly/3Kb33oE",
            )

    def _create_text_clip(
        self, text: str, emoji: str, duration: float, fontsize: int, cfg: AppConfig
    ):
        from moviepy.editor import ImageClip  # type: ignore[import]
        from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

        width, height = 1080, 200
        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)
        font_path = os.path.join(cfg.fonts_dir, "Roboto_Condensed-Black.ttf")
        try:
            text_font = ImageFont.truetype(font_path, fontsize)
        except Exception:
            text_font = ImageFont.load_default()

        emoji_font = None
        for path in ["C:/Windows/Fonts/seguiemj.ttf", "/System/Library/Fonts/Apple Color Emoji.ttc"]:
            if os.path.isfile(path):
                try:
                    emoji_font = ImageFont.truetype(path, fontsize)
                    break
                except Exception:
                    pass

        text_bbox = draw.textbbox((0, 0), text, font=text_font)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]
        ew = eh = 0
        if emoji_font:
            ebbox = draw.textbbox((0, 0), emoji, font=emoji_font)
            ew = ebbox[2] - ebbox[0]
            eh = ebbox[3] - ebbox[1]

        total_w = tw + ew
        start_x = (width - total_w) // 2
        text_y = (height - max(th, eh)) // 2

        # Drop shadow
        if cfg.text_shadow:
            off = cfg.text_shadow_offset
            draw.text(
                (start_x + off, text_y + off), text,
                font=text_font, fill=cfg.text_shadow_color,
                stroke_width=2, stroke_fill=cfg.text_shadow_color,
            )

        # Main text with configurable color + stroke
        draw.text(
            (start_x, text_y), text,
            font=text_font, fill=cfg.text_color,
            stroke_width=3, stroke_fill=cfg.text_stroke_color,
        )
        if emoji_font:
            draw.text((start_x + tw, text_y + 10), emoji, font=emoji_font, fill="white", embedded_color=True)

        tmp_png = tempfile.mktemp(suffix=".png")
        image.save(tmp_png)
        clip = ImageClip(tmp_png).set_duration(duration)
        os.remove(tmp_png)
        return clip

    def _create_subtitle_clips(
        self, text: str, audio_path: str, fontsize: int, cfg: AppConfig
    ):
        from moviepy.editor import TextClip, concatenate_videoclips  # type: ignore[import]
        from pydub import AudioSegment  # type: ignore[import]

        audio = AudioSegment.from_file(audio_path)
        total_dur = audio.duration_seconds
        font_path = os.path.join(cfg.fonts_dir, "Roboto_Condensed-Black.ttf")
        if not os.path.isfile(font_path):
            font_path = None

        lines = textwrap.wrap(text, width=13)
        dur_per_line = total_dur / max(len(lines), 1)
        clips = [
            TextClip(
                line, fontsize=fontsize,
                color=cfg.text_color, font=font_path,
                stroke_width=3, stroke_color=cfg.text_stroke_color,
                method="caption", size=(1000, None),
            ).set_duration(dur_per_line)
            for line in lines
        ]
        return concatenate_videoclips(clips)

    @staticmethod
    def _save_details(out_dir: str, game: str, video_id: int, title: str, description: str) -> None:
        filename = os.path.join(out_dir, f"{game}-{video_id}_details.txt")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Title: {title}\n")
                f.write("-" * 20 + "\n")
                f.write(f"Description: {description}\n")
        except OSError as exc:
            log.warning("Could not write details file: %s", exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Game highlight short video maker")
    p.add_argument("--game-name", required=True, help="Game name, e.g. 'Counter-Strike'")
    p.add_argument("--video-id", type=int, default=None, help="Specific video ID (manual mode)")
    p.add_argument("--video-title", default="", help="Video title (manual mode)")
    p.add_argument("--url", default=None, help="Twitch VOD/playlist URL to download first")
    p.add_argument("--input-dir", default=None)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--music-folder", default=None)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--auto", dest="auto_mode", action="store_true", default=True,
                      help="Auto-detect next unprocessed video ID (default)")
    mode.add_argument("--no-auto", dest="auto_mode", action="store_false",
                      help="Use selected_videos.txt for ID and title")
    p.add_argument("--config", default="config/default_config.toml")
    return p


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    cfg = load_config(args.config)
    if args.input_dir:
        cfg.input_dir = args.input_dir
    if args.output_dir:
        cfg.output_dir = args.output_dir
    if args.music_folder:
        cfg.music_folder = args.music_folder

    pipeline = GameHighlightPipeline(config=cfg)
    pipeline.run(
        game_name=args.game_name,
        video_id=args.video_id,
        video_title=args.video_title,
        source=args.url or "",
        source_type="url" if args.url else "local",
        auto_mode=args.auto_mode,
    )


if __name__ == "__main__":
    main()
