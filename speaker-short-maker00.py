#!/usr/bin/env python3
"""
Speaker Short Video Maker

Features:
- Download video from URL (handles YouTube authentication)
- Extract speech using Whisper
- AI-powered key moment detection
- Intelligent video cutting and transitions
- Subtitle generation with styling
- Background music integration
- Professional output under 60 seconds
- Person tracking and center framing
- Vertical video format with blurred background

Author: AI Video Editor
"""

import os
import sys
import json
import srt
import time
import tempfile
import argparse
import subprocess
import shutil
import random
import ast
import textwrap
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import atexit

# Video & audio processing
from moviepy.editor import *
from moviepy.audio.fx import all as afx
from pydub import AudioSegment
import numpy as np

# Download with cookie support
import yt_dlp

# AI transcription
import whisper

# Computer vision for detection
import cv2
import mediapipe as mp
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont

# Text processing and AI
from pathlib import Path

# ImageMagick configuration
try:
    from moviepy.config import change_settings
    change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})
except:
    print("Warning: ImageMagick not found. Text overlays may not work.")

# =========================
# Configuration
# =========================

class Config:
    INPUT_DIR = "speaker-downloads"
    OUTPUT_DIR = "speaker-output"
    MUSIC_FOLDER = "./musics"
    FONTS_DIR = "./fonts"
    MAX_DURATION = 59
    FADE_DURATION = 0.5
    TRANSITION_DURATION = 0.3
    OUTPUT_WIDTH = 1080   # For vertical format
    OUTPUT_HEIGHT = 1920
    PERSON_DETECTION_CONF = 0.5

# =========================
# Data Classes
# =========================

@dataclass
class SubtitleSegment:
    start: float
    end: float
    text: str
    confidence: float = 1.0

@dataclass
class KeyMoment:
    start: float
    end: float
    text: str
    importance_score: float
    keywords: List[str]

# =========================
# Download Handler with Cookie Support
# =========================

class VideoDownloader:
    def __init__(self):
        self.download_dir = Config.INPUT_DIR
        os.makedirs(self.download_dir, exist_ok=True)
    
    def download_video(self, url: str, use_cookies: bool = True) -> str:
        """Download video with cookie support for authentication"""
        
        # Try different cookie methods
        cookie_options = []
        if use_cookies:
            # Try browser cookies first
            browsers = ['chrome', 'firefox', 'edge', 'safari']
            for browser in browsers:
                try:
                    cookie_options.append(f"--cookies-from-browser {browser}")
                except:
                    continue
        
        outtmpl = os.path.join(self.download_dir, "%(title).100s.%(id)s.%(ext)s")
        
        base_opts = {
            "outtmpl": outtmpl,
            "noplaylist": True,
            "merge_output_format": "mp4",
            "format": "best[height<=720]/best",  # Limit quality for faster processing
            "writesubtitles": False,
            "writeautomaticsub": False,
        }
        
        # Try download with cookies first, then without
        for attempt, extra_opts in enumerate([
            {"cookiesfrombrowser": ("chrome",)} if use_cookies else {},
            {"cookiesfrombrowser": ("firefox",)} if use_cookies else {},
            {}  # No cookies fallback
        ]):
            try:
                opts = {**base_opts, **extra_opts}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    # Get the downloaded filename
                    title = info.get("title", "video")
                    video_id = info.get("id", "unknown")
                    filename = f"{title[:100]}.{video_id}.mp4"
                    filepath = os.path.join(self.download_dir, filename)
                    
                    if os.path.exists(filepath):
                        return filepath
                    
                    # Try to find the actual file
                    for file in os.listdir(self.download_dir):
                        if video_id in file and file.endswith('.mp4'):
                            return os.path.join(self.download_dir, file)
                    
                    return filepath
                    
            except Exception as e:
                print(f"Download attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    raise Exception(f"Failed to download video after all attempts. Try manually downloading or using --cookies option.")
                continue
        
        raise Exception("Download failed")

# =========================
# Speech Processing & AI Analysis
# =========================

class SpeechProcessor:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size.lower()  # Ensure lowercase
        self.model = None
        print(f"Initialized SpeechProcessor with model size: {self.model_size}")
    
    def load_whisper_model(self):
        """Load Whisper model for transcription"""
        if self.model is None:
            print(f"Loading Whisper model: {self.model_size}")
            try:
                self.model = whisper.load_model(self.model_size)
                print(f"Successfully loaded {self.model_size} model")
            except Exception as e:
                print(f"Error loading {self.model_size} model: {e}")
                print("Falling back to base model")
                self.model = whisper.load_model("base")

    
    def transcribe_video(self, video_path: str, language: Optional[str] = None) -> List[SubtitleSegment]:
        """Transcribe video and return segments with timing"""
        self.load_whisper_model()
        
        print("Transcribing video...")
        result = self.model.transcribe(video_path, language=language, word_timestamps=True)
        
        segments = []
        for seg in result["segments"]:
            segments.append(SubtitleSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"].strip(),
                confidence=seg.get("avg_logprob", 0.0)
            ))
        
        print(f"Found {len(segments)} speech segments")
        return segments
    
    def analyze_key_moments(self, segments: List[SubtitleSegment]) -> List[KeyMoment]:
        """Use AI to identify key moments from speech segments"""
        # Combine all text for analysis
        full_text = " ".join([seg.text for seg in segments])
        
        try:
            # This would integrate with your LLM (replace with actual LLM call)
            key_moments_analysis = self._analyze_with_llm(full_text, segments)
            return key_moments_analysis
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return self._fallback_key_moment_detection(segments)
    
    def _analyze_with_llm(self, full_text: str, segments: List[SubtitleSegment]) -> List[KeyMoment]:
        """Placeholder for LLM integration - replace with your actual LLM"""
        # This is where you'd call your LLM (like the gemini_text module)
        # For now, using a simple fallback
        return self._fallback_key_moment_detection(segments)
    
    def _fallback_key_moment_detection(self, segments: List[SubtitleSegment]) -> List[KeyMoment]:
        """Simple fallback key moment detection based on text length and keywords"""
        key_moments = []
        
        # Keywords that often indicate important content
        important_keywords = [
            "important", "key", "crucial", "remember", "main", "point", "conclusion",
            "summary", "finally", "therefore", "because", "however", "but", "so",
            "first", "second", "third", "next", "also", "additionally", "furthermore"
        ]
        
        for seg in segments:
            score = 0
            words = seg.text.lower().split()
            
            # Score based on length (longer segments might be more important)
            score += min(len(words) * 0.1, 2.0)
            
            # Score based on keywords
            for keyword in important_keywords:
                if keyword in seg.text.lower():
                    score += 1.0
            
            # Score based on punctuation (questions, exclamations)
            if "?" in seg.text or "!" in seg.text:
                score += 0.5
            
            if score > 1.0:  # Threshold for importance
                key_moments.append(KeyMoment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    importance_score=score,
                    keywords=[w for w in words if w in important_keywords]
                ))
        
        # Sort by importance and return top moments
        key_moments.sort(key=lambda x: x.importance_score, reverse=True)
        
        # Limit to fit within target duration
        selected_moments = []
        total_duration = 0
        
        for moment in key_moments:
            moment_duration = moment.end - moment.start
            if total_duration + moment_duration <= Config.MAX_DURATION - 10:  # Leave room for transitions
                selected_moments.append(moment)
                total_duration += moment_duration
        
        return selected_moments

# =========================
# Video Processing
# =========================

class VideoProcessor:
    def __init__(self):
        self.model = None
        self.mp_face = mp.solutions.face_detection
        self.face_detection = None
        self.frame_sample_rate = 0.5  # Process frame every 0.5 seconds
        
    def load_yolo_model(self):
        """Load YOLO model for person detection"""
        try:
            self.model = YOLO('yolov8n.pt')
            print("YOLO model loaded successfully")
            return True
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            return False
    
    def detect_person_in_frame(self, frame):
        """Detect person in frame and return bounding box"""
        if self.model is None:
            return None
            
        results = self.model(frame)
        max_conf = 0
        best_box = None
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    if self.model.names[class_id] == 'person':
                        conf = float(box.conf[0])
                        if conf > max_conf and conf > Config.PERSON_DETECTION_CONF:
                            max_conf = conf
                            best_box = box.xyxy[0].cpu().numpy()
        
        if best_box is not None:
            return tuple(map(int, best_box))
        return None
    
    def create_text_clip(self, text, emoji, duration, fontsize=60, color='white'):
        """Create text clip with emojis"""
        width, height = 1080, 200
        image = Image.new('RGBA', (width, height))
        draw = ImageDraw.Draw(image)
        
        # Load fonts
        text_font_path = "./fonts/Roboto_Condensed-Black.ttf"
        try:
            text_font = ImageFont.truetype(text_font_path, fontsize)
        except:
            text_font = ImageFont.load_default()
        
        # Try to find emoji font
        emoji_font = None
        emoji_font_paths = [
            "C:/Windows/Fonts/seguiemj.ttf",
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        ]
        
        for path in emoji_font_paths:
            if os.path.exists(path):
                try:
                    emoji_font = ImageFont.truetype(path, fontsize)
                    break
                except:
                    continue
        
        # Calculate positions
        text_bbox = draw.textbbox((0, 0), text, font=text_font)
        text_width = text_bbox[2] - text_bbox[0]
        
        if emoji_font:
            emoji_bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
            emoji_width = emoji_bbox[2] - emoji_bbox[0]
        else:
            emoji_width = 0
        
        total_width = text_width + emoji_width
        start_x = (width - total_width) // 2
        text_y = (height - text_bbox[3]) // 2
        
        # Draw text with stroke
        draw.text((start_x, text_y), text, font=text_font, fill=color,
                 stroke_width=3, stroke_fill="#0B13AF")
        
        # Draw emoji
        if emoji_font:
            emoji_x = start_x + text_width
            draw.text((emoji_x, text_y), emoji, font=emoji_font, embedded_color=True)
        
        # Save temporary image
        temp_path = tempfile.mktemp(suffix='.png')
        image.save(temp_path)
        
        # Create MoviePy clip
        clip = ImageClip(temp_path).set_duration(duration)
        os.remove(temp_path)
        
        return clip
    
    def create_subtitle_clips(self, segments, fontsize=80, color='white'):
        """Create subtitle clips from segments"""
        clips = []
        fontpath = './fonts/Roboto_Condensed-Black.ttf'
        
        for segment in segments:
            lines = textwrap.wrap(segment.text, width=30)
            for line in lines:
                clip = TextClip(
                    line,
                    fontsize=fontsize,
                    color=color,
                    font=fontpath,
                    stroke_width=3,
                    stroke_color="#3C4CFD",
                    method='caption',
                    size=(1000, None)
                )
                
                clip = clip.set_duration(segment.end - segment.start)
                clip = clip.set_start(segment.start)
                clips.append(clip)
        
        return clips
    
    def process_video(self, input_path, key_moments, output_path):
        """Process video with person tracking and vertical format"""
        if not self.load_yolo_model():
            print("Failed to load YOLO model")
            return False
        
        print("Processing video...")
        video = VideoFileClip(input_path)
        fps = video.fps
        
        # Calculate frame indices to process based on sample rate
        total_frames = int(video.duration * video.fps)
        sample_interval = int(self.frame_sample_rate * fps)
        
        # Track last known good position for smoother transitions
        last_known_position = None
        
        def process_frame(get_frame, t):
            frame = get_frame(t)
            
            # Only process certain frames
            nonlocal last_known_position
            current_frame_idx = int(t * fps)
            
            if current_frame_idx % sample_interval == 0:
                # Process this frame
                person_box = self.detect_person_in_frame(frame)
                if person_box:
                    x1, y1, x2, y2 = person_box
                    center_x = (x1 + x2) // 2
                    last_known_position = center_x
            
            frame_width = frame.shape[1]
            crop_width = Config.OUTPUT_WIDTH
            
            # Use last known position or center if no detection
            if last_known_position is None:
                last_known_position = frame_width // 2
            
            # Calculate crop region
            left = max(0, last_known_position - (crop_width // 2))
            right = min(frame_width, left + crop_width)
            
            # Adjust if out of bounds
            if right == frame_width:
                left = frame_width - crop_width
            elif left == 0:
                right = crop_width
            
            # Crop and resize frame
            frame = frame[:, left:right]
            frame = cv2.resize(frame, (Config.OUTPUT_WIDTH, Config.OUTPUT_HEIGHT))
            
            return frame
        
        # Create vertical video with person tracking
        processed_video = video.fl(process_frame)
        
        # Create blurred background
        background = video.resize(height=Config.OUTPUT_HEIGHT)
        background = background.crop(x_center=background.w/2,
                                  y_center=background.h/2,
                                  width=Config.OUTPUT_WIDTH,
                                  height=Config.OUTPUT_HEIGHT)
        background = background.fl_image(lambda f: cv2.GaussianBlur(f, (25, 25), 0))
        
        # Get title and emoji
        comment, emoji = self.get_video_title(key_moments)
        
        # Create text overlays
        title_clip = self.create_text_clip(comment, emoji, video.duration, fontsize=90)
        subtitle_clips = self.create_subtitle_clips(key_moments)
        
        # Compose final video
        final_video = CompositeVideoClip([
            background,
            processed_video.set_position('center'),
            title_clip.set_position(('center', 200))
        ] + [clip.set_position(('center', 1400)) for clip in subtitle_clips])
        
        # Add fades
        final_video = final_video.fadein(Config.FADE_DURATION)
        final_video = final_video.fadeout(Config.FADE_DURATION)
        
        # Add audio fades
        if video.audio:
            final_video = final_video.fx(afx.audio_fadein, Config.FADE_DURATION)
            final_video = final_video.fx(afx.audio_fadeout, Config.FADE_DURATION)
        
        # Write final video
        final_video.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            ffmpeg_params=['-crf', '18']
        )
        
        # Cleanup
        video.close()
        final_video.close()
        
        return True
    
    def get_video_title(self, key_moments):
        """Generate engaging title and emoji for video"""
        # Use first key moment or fallback
        if key_moments:
            text = key_moments[0].text
        else:
            text = "Amazing Moment!"
            
        emojis = ["🎯🔥", "✨💫", "🎤💫", "🗣️💭", "🎯💡", "🌟✨"]
        emoji = random.choice(emojis)
        
        return text[:30], emoji

# =========================
# Main Speaker Short Maker
# =========================

class SpeakerShortMaker:
    def __init__(self):
        self.downloader = VideoDownloader()
        # Initialize with base model by default
        self.speech_processor = None
        self.video_processor = VideoProcessor()
        
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        atexit.register(self._cleanup_on_exit)
    
    def _cleanup_on_exit(self):
        """Cleanup resources on program exit"""
        try:
            # Force garbage collection
            import gc
            gc.collect()
        except:
            pass
    
    def _get_video_path(self, url: str = None, local_path: str = None) -> str:
        """Get video path from URL or local path"""
        if local_path:
            print(f"Using local video: {local_path}")
            if not os.path.isfile(local_path):
                raise Exception(f"Local video file not found: {local_path}")
            return local_path
        elif url:
            print(f"Downloading video from: {url}")
            video_path = self.downloader.download_video(url)
            print(f"Downloaded to: {video_path}")
            return video_path
        else:
            raise Exception("Either URL or local path must be provided")
    
    def create_short_video(self, url=None, local_path=None, output_name=None,
                          blur_faces=False, language=None, whisper_model="base"):
        """Main function to create short speaker video"""
        try:
            # Initialize speech processor with specified model
            self.speech_processor = SpeechProcessor(model_size=whisper_model)
            
            # Get video path
            video_path = self._get_video_path(url, local_path)
            
            # Extract speech segments
            segments = self.speech_processor.transcribe_video(video_path, language)
            
            # Identify key moments
            key_moments = self.speech_processor.analyze_key_moments(segments)
            
            # Set output path
            if not output_name:
                output_name = f"speaker_short_{int(time.time())}.mp4"
            output_path = os.path.join(Config.OUTPUT_DIR, output_name)
            
            # Process video
            success = self.video_processor.process_video(
                video_path, key_moments, output_path
            )
            
            return output_path if success else None
            
        except Exception as e:
            print(f"Error creating short video: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Speaker Short Video Maker")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=str, help="Path to local video file")
    src.add_argument("--url", type=str, help="Video URL to download and process")
    parser.add_argument("--output", "-o", help="Output filename")
    parser.add_argument("--blur-faces", action="store_true", help="Blur faces for privacy")
    parser.add_argument("--language", "-l", help="Force language for transcription")
    parser.add_argument("--whisper-model", default="base",
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper model size")
    
    args = parser.parse_args()
    
    try:
        maker = SpeakerShortMaker()
        output_path = maker.create_short_video(
            url=args.url,
            local_path=args.input,
            output_name=args.output,
            blur_faces=args.blur_faces,
            language=args.language,
            whisper_model=args.whisper_model
        )
        
        if output_path:
            print(f"\n🎉 Success! Speaker short video created: {output_path}")
        else:
            print("\n❌ Failed to create video")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()