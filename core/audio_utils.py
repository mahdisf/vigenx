from __future__ import annotations

import logging
import os
import subprocess
from typing import Optional

import librosa
import numpy as np

log = logging.getLogger(__name__)


def extract_audio_wav(video_path: str, out_path: str, sample_rate: int = 16000) -> str:
    """Extract mono WAV from video via ffmpeg."""
    subprocess.check_call(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-ac", "1", "-ar", str(sample_rate), out_path,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return out_path


def detect_voiced_intervals(
    audio_path: str,
    frame_length: int = 2048,
    hop_length: int = 512,
    top_db: float = 28.0,
) -> list[tuple[float, float]]:
    """Return (start_sec, end_sec) tuples for non-silent intervals."""
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    intervals = librosa.effects.split(
        y, top_db=top_db, frame_length=frame_length, hop_length=hop_length
    )
    return [(int(s) / sr, int(e) / sr) for s, e in intervals]


def get_video_duration(video_path: str) -> float:
    """Return duration in seconds via ffprobe (robust for most containers)."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format=duration",
            "-of", "default=nk=1:nw=1",
            video_path,
        ]
        out = subprocess.check_output(cmd).decode().strip()
        return float(out)
    except Exception:
        from moviepy.editor import VideoFileClip  # type: ignore[import]
        with VideoFileClip(video_path) as clip:
            return clip.duration
