#!/usr/bin/env python3
"""
AI Video Editor (download -> edit -> export)

Features (toggle with CLI flags):
- URL/file input (auto-download via yt-dlp)
- Whisper speech-to-text -> burn-in subtitles
- Silence trimming (energy-based via librosa)
- Scene detection (PySceneDetect)
- Face blur (MediaPipe + OpenCV)
- Final export (H.264 + AAC)

Author: You :)
"""

import os
import sys
import math
import json
import srt
import time
import tempfile
import argparse
import subprocess
from dataclasses import dataclass
from typing import List, Tuple, Optional

# --- Video & audio libs
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip,
    concatenate_videoclips, vfx
)
import numpy as np

# --- Download
import yt_dlp

# --- AI / DSP
import whisper
import librosa

# --- CV
import cv2
import mediapipe as mp

# --- Scene detect
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

# --- Utils
from tqdm import tqdm


# =========================
# Helpers
# =========================

def ffprobe_duration(path: str) -> float:
    """Get duration using ffprobe (more robust than MoviePy for some containers)."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", path
        ]
        out = subprocess.check_output(cmd).decode().strip()
        return float(out)
    except Exception:
        # fallback to MoviePy
        return VideoFileClip(path).duration


def download_video(url: str, out_dir: str) -> str:
    """Download video via yt-dlp, return filepath."""
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(title).200s.%(ext)s")
    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "format": "bv*+ba/b",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "_filename" in info:
            return info["_filename"]
        # Construct expected path
        title = info.get("title", "video")
        ext = info.get("ext", "mp4")
        return os.path.join(out_dir, f"{title}.{ext}")


# =========================
# Whisper Transcription & Subtitles
# =========================

@dataclass
class SubtitleSegment:
    start: float
    end: float
    text: str

def transcribe_whisper(audio_video_path: str, model_size: str = "small", language: Optional[str] = None) -> List[SubtitleSegment]:
    """
    Transcribe with Whisper. Returns segment list.
    """
    print(f"[Whisper] Loading model: {model_size}")
    model = whisper.load_model(model_size)
    print("[Whisper] Transcribing...")
    result = model.transcribe(audio_video_path, language=language)
    segments = []
    for seg in result["segments"]:
        segments.append(SubtitleSegment(seg["start"], seg["end"], seg["text"].strip()))
    print(f"[Whisper] Segments: {len(segments)}")
    return segments

def write_srt(segments: List[SubtitleSegment], srt_path: str):
    srt_items = []
    for i, seg in enumerate(segments, 1):
        srt_items.append(srt.Subtitle(index=i,
                                      start=srt.timedelta(seconds=seg.start),
                                      end=srt.timedelta(seconds=seg.end),
                                      content=seg.text))
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(srt_items))

def burn_subtitles(clip: VideoFileClip, segments: List[SubtitleSegment], font_size: int = 42) -> CompositeVideoClip:
    """
    Burn-in subtitles using MoviePy TextClip per segment.
    Note: This is computationally heavy for long videos.
    """
    overlays = []
    h = clip.h
    for seg in segments:
        txt = TextClip(seg.text, fontsize=font_size, color='white', stroke_color='black', stroke_width=2, method='caption', align='center', size=(int(clip.w*0.9), None))
        txt = txt.set_start(max(seg.start, 0)).set_end(seg.end)
        txt = txt.set_position(("center", h - int(h*0.15)))
        overlays.append(txt)
    return CompositeVideoClip([clip, *overlays])


# =========================
# Silence Trimming (Librosa)
# =========================

def detect_voiced_intervals(audio_path: str, frame_length=2048, hop_length=512, top_db=28) -> List[Tuple[float, float]]:
    """
    Returns list of (start_sec, end_sec) for non-silent intervals based on energy.
    """
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    intervals = librosa.effects.split(y, top_db=top_db, frame_length=frame_length, hop_length=hop_length)
    voiced = []
    for start, end in intervals:
        voiced.append((start / sr, end / sr))
    return voiced

def trim_video_to_intervals(clip: VideoFileClip, intervals: List[Tuple[float, float]], pad: float = 0.05) -> VideoFileClip:
    """
    Concatenate only the voiced intervals (+/- pad).
    """
    subclips = []
    for (s, e) in intervals:
        s2 = max(0, s - pad)
        e2 = min(clip.duration, e + pad)
        if e2 > s2:
            subclips.append(clip.subclip(s2, e2))
    if not subclips:
        return clip
    return concatenate_videoclips(subclips, method="compose")


# =========================
# Scene Detection (PySceneDetect)
# =========================

def detect_scenes(path: str, threshold: float = 27.0) -> List[Tuple[float, float]]:
    """
    Returns a list of (start_sec, end_sec) scene intervals based on content detector.
    """
    video_manager = VideoManager([path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    base_timecode = None
    try:
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list(base_timecode)
        intervals = []
        # If base_timecode is None, PySceneDetect uses internally computed timecodes; we fetch via VideoManager
        duration = ffprobe_duration(path)
        last_start = 0.0
        for start_time, end_time in scene_list:
            s = start_time.get_seconds()
            e = end_time.get_seconds()
            intervals.append((s, e))
            last_start = e
        if not intervals:
            return [(0.0, duration)]
        # Ensure cover to end
        if intervals[-1][1] < duration:
            intervals[-1] = (intervals[-1][0], duration)
        return intervals
    finally:
        video_manager.release()


# =========================
# Face Blur (MediaPipe + OpenCV)
# =========================

mp_face = mp.solutions.face_detection

def build_face_blur_filter(blur_ksize: int = 61, expand: float = 0.35):
    """
    Returns a frame processor that blurs detected faces.
    expand: expands bbox by % of box size for nicer blur coverage.
    """
    face_det = mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5)

    def process_frame(frame: np.ndarray) -> np.ndarray:
        # frame: RGB (MoviePy provides RGB)
        h, w, _ = frame.shape
        img_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        img_rgb = frame  # already RGB
        results = face_det.process(img_rgb)
        if results.detections:
            for det in results.detections:
                bb = det.location_data.relative_bounding_box
                x = max(0, int(bb.xmin * w))
                y = max(0, int(bb.ymin * h))
                bw = int(bb.width * w)
                bh = int(bb.height * h)
                # expand
                x_e = max(0, int(x - expand * bw))
                y_e = max(0, int(y - expand * bh))
                bw_e = min(w - x_e, int(bw * (1 + 2*expand)))
                bh_e = min(h - y_e, int(bh * (1 + 2*expand)))

                roi = img_bgr[y_e:y_e+bh_e, x_e:x_e+bw_e]
                if roi.size > 0:
                    roi_blur = cv2.GaussianBlur(roi, (blur_ksize, blur_ksize), 0)
                    img_bgr[y_e:y_e+bh_e, x_e:x_e+bw_e] = roi_blur

        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    return process_frame


# =========================
# Pipeline
# =========================

def main():
    parser = argparse.ArgumentParser(description="AI-based video editor (download -> edit -> export)")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=str, help="Path to local video file")
    src.add_argument("--url", type=str, help="URL to download (yt-dlp)")

    parser.add_argument("--out", type=str, default="output.mp4", help="Output MP4 path")

    # AI features
    parser.add_argument("--whisper", action="store_true", help="Transcribe & burn-in subtitles with Whisper")
    parser.add_argument("--whisper-model", type=str, default="small", help="Whisper model size (tiny/base/small/medium/large)")
    parser.add_argument("--language", type=str, default=None, help="Force language for Whisper (e.g., en, fa)")

    parser.add_argument("--trim-silence", action="store_true", help="Trim silent parts (energy-based)")
    parser.add_argument("--silence-topdb", type=float, default=28.0, help="Silence threshold (lower = keep more)")
    parser.add_argument("--silence-pad", type=float, default=0.05, help="Padding seconds around voiced intervals")

    parser.add_argument("--scene-detect", action="store_true", help="Detect scenes (report only)")
    parser.add_argument("--scene-threshold", type=float, default=27.0, help="Scene detection threshold")

    parser.add_argument("--blur-faces", action="store_true", help="Blur faces (MediaPipe FaceDetection)")
    parser.add_argument("--blur-ksize", type=int, default=61, help="Gaussian blur kernel (odd number)")
    parser.add_argument("--blur-expand", type=float, default=0.35, help="Expand bbox percent")

    parser.add_argument("--start", type=float, default=0.0, help="Optional start time (sec)")
    parser.add_argument("--end", type=float, default=None, help="Optional end time (sec)")

    parser.add_argument("--fps", type=int, default=None, help="Override output fps")
    parser.add_argument("--crf", type=int, default=18, help="x264 CRF (lower = higher quality)")
    parser.add_argument("--preset", type=str, default="medium", help="x264 preset: ultrafast..veryslow")
    parser.add_argument("--audio-bitrate", type=str, default="192k", help="AAC audio bitrate")

    args = parser.parse_args()

    tmp = tempfile.mkdtemp(prefix="ai_vid_")
    print(f"[TMP] {tmp}")

    # 1) Resolve input path (download if URL)
    if args.url:
        print(f"[Download] {args.url}")
        in_path = download_video(args.url, tmp)
        print(f"[Download] Saved -> {in_path}")
    else:
        in_path = args.input
        if not os.path.isfile(in_path):
            print(f"Input file not found: {in_path}", file=sys.stderr)
            sys.exit(1)

    duration = ffprobe_duration(in_path)
    start = max(0.0, args.start)
    end = args.end if args.end is not None else duration
    end = min(end, duration)
    if end <= start:
        print("Invalid start/end", file=sys.stderr)
        sys.exit(1)

    # 2) Load clip
    print("[MoviePy] Loading clip...")
    clip = VideoFileClip(in_path).subclip(start, end)

    # 3) Optional: face blur (frame-by-frame)
    if args.blur_faces:
        print("[FaceBlur] Applying face blur...")
        processor = build_face_blur_filter(args.blur_ksize, args.blur_expand)
        def fl_image(frame):
            return processor(frame)
        clip = clip.fl_image(fl_image)

    # 4) Optional: silence trim
    if args.trim_silence:
        print("[SilenceTrim] Extracting audio & detecting voiced intervals...")
        audio_tmp = os.path.join(tmp, "audio.wav")
        # Extract audio via ffmpeg to avoid resampling issues
        subprocess.check_call([
            "ffmpeg", "-y", "-i", in_path, "-vn", "-ac", "1", "-ar", "16000", audio_tmp
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        intervals = detect_voiced_intervals(audio_tmp, top_db=args.silence_topdb)
        print(f"[SilenceTrim] Found {len(intervals)} voiced intervals.")
        if intervals:
            # shift intervals by 'start' because we subclipped
            intervals = [(max(0.0, s - start), max(0.0, e - start)) for (s, e) in intervals if e > start and s < end]
            clip = trim_video_to_intervals(clip, intervals, pad=args.silence_pad)
        else:
            print("[SilenceTrim] No voiced intervals detected; skipping.")

    # 5) Optional: scene detection (report)
    if args.scene_detect:
        print("[SceneDetect] Detecting scenes...")
        scenes = detect_scenes(in_path, threshold=args.scene_threshold)
        # Clip range filter
        scenes = [(max(0.0, s - start), max(0.0, e - start)) for (s, e) in scenes if e > start and s < end]
        print(f"[SceneDetect] Scenes in selected range: {len(scenes)}")
        for i, (s, e) in enumerate(scenes, 1):
            print(f"  - Scene {i:02d}: {s:.2f}s -> {e:.2f}s  ({e - s:.2f}s)")

    # 6) Optional: Whisper subtitles (burn-in)
    if args.whisper:
        print("[Subtitles] Transcribing with Whisper...")
        # Better to transcribe original (not already-processed) region to keep sync
        # Extract the selected region to temp for precise timing
        region_path = os.path.join(tmp, "region.mp4")
        subprocess.check_call([
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", in_path,
            "-c", "copy", region_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        segments = transcribe_whisper(region_path, model_size=args.whisper_model, language=args.language)
        if segments:
            print("[Subtitles] Burning-in...")
            clip = burn_subtitles(clip, segments, font_size=42)
        else:
            print("[Subtitles] No segments found; skipping.")

    # 7) Export
    print("[Export] Writing output...")
    # Respect original fps if not overridden
    export_fps = args.fps or getattr(clip, "fps", None) or 30

    clip.write_videofile(
        args.out,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate=args.audio_bitrate,
        temp_audiofile=os.path.join(tmp, "temp-audio.m4a"),
        remove_temp=True,
        threads=os.cpu_count(),
        fps=export_fps,
        preset=args.preset,
        ffmpeg_params=["-crf", str(args.crf)]
    )

    print(f"[Done] Saved -> {args.out}")


if __name__ == "__main__":
    main()
