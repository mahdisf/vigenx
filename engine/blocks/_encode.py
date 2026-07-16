"""Shared MP4 encode settings for the Export and Export Clips blocks.

Centralizes the user-facing dropdowns (quality / fps / codec / audio codec /
bitrate / preset) and the translation of those choices into the ffmpeg arguments
MoviePy's ``write_videofile`` expects, so both export blocks stay consistent.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from engine.block import ParamSpec

# Quality label -> CRF (lower = better quality / bigger file).
QUALITY = {"Lossless": 0, "High": 18, "Medium": 23, "Low": 28, "Very low": 32}
QUALITY_CHOICES = list(QUALITY)
FPS_CHOICES = ["source", "24", "30", "60"]
CODEC_CHOICES = ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "mpeg4"]
AUDIO_CODEC_CHOICES = ["aac", "libmp3lame", "ac3"]
AUDIO_BITRATE_CHOICES = ["96k", "128k", "192k", "256k", "320k"]
PRESET_CHOICES = ["ultrafast", "superfast", "veryfast", "faster", "fast",
                  "medium", "slow", "slower", "veryslow"]


def encode_param_specs() -> List[ParamSpec]:
    """The shared encode dropdowns shown on both export blocks."""
    return [
        ParamSpec("quality", "enum", "High", choices=QUALITY_CHOICES, label="Quality"),
        ParamSpec("fps", "enum", "source", choices=FPS_CHOICES, label="FPS"),
        ParamSpec("codec", "enum", "libx264", choices=CODEC_CHOICES, advanced=True,
                  label="Video codec"),
        ParamSpec("audio_codec", "enum", "aac", choices=AUDIO_CODEC_CHOICES,
                  advanced=True, label="Audio codec"),
        ParamSpec("audio_bitrate", "enum", "192k", choices=AUDIO_BITRATE_CHOICES,
                  advanced=True, label="Audio bitrate"),
        ParamSpec("preset", "enum", "medium", choices=PRESET_CHOICES, advanced=True,
                  label="Encode preset"),
    ]


@dataclass
class EncodeSettings:
    codec: str
    crf: int
    fps: Optional[float]
    audio_codec: str
    audio_bitrate: str
    preset: str


def resolve_encode(block, clip, cfg) -> EncodeSettings:
    """Translate a block's dropdown selections into concrete encode settings."""
    crf = QUALITY.get(block.p("quality", "High"), 18)
    fps_choice = str(block.p("fps", "source"))
    if fps_choice == "source":
        fps = getattr(clip, "fps", None) or getattr(cfg, "output_fps", 30)
    else:
        fps = int(fps_choice)
    return EncodeSettings(
        codec=block.p("codec", "libx264"),
        crf=crf,
        fps=fps,
        audio_codec=block.p("audio_codec", "aac"),
        audio_bitrate=block.p("audio_bitrate", "192k"),
        preset=block.p("preset", "medium"),
    )


def write_video(clip, out_path: str, enc: EncodeSettings, ctx, tag: str = "export") -> None:
    """Render ``clip`` to ``out_path`` using ``enc``."""
    clip.write_videofile(
        out_path,
        codec=enc.codec,
        audio_codec=enc.audio_codec,
        audio_bitrate=enc.audio_bitrate,
        temp_audiofile=ctx.temp_path(f"{tag}-audio.m4a"),
        remove_temp=True,
        threads=os.cpu_count(),
        fps=enc.fps,
        preset=enc.preset,
        ffmpeg_params=["-crf", str(enc.crf)],
        verbose=False,
        logger=None,
    )


__all__ = [
    "QUALITY", "QUALITY_CHOICES", "FPS_CHOICES", "CODEC_CHOICES",
    "AUDIO_CODEC_CHOICES", "AUDIO_BITRATE_CHOICES", "PRESET_CHOICES",
    "encode_param_specs", "EncodeSettings", "resolve_encode", "write_video",
]
