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

# Computer vision for face detection
import cv2
import mediapipe as mp

# Text processing and AI
from pathlib import Path

# ImageMagick configuration (adjust path as needed)
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
    MAX_DURATION = 59  # Maximum output duration in seconds
    FADE_DURATION = 0.5
    TRANSITION_DURATION = 0.3

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
    def __init__(self, model_size: str = "small"):
        self.model_size = model_size
        self.model = None
    
    def load_whisper_model(self):
        """Load Whisper model for transcription"""
        if self.model is None:
            print(f"Loading Whisper model: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
    
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
        # This is where you'd call your LLM (for example, gemini_client.generate_text).
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
        self.mp_face = mp.solutions.face_detection
        self.face_detection = None
    
    def load_face_detection(self):
        """Load MediaPipe face detection for blur effects"""
        if self.face_detection is None:
            self.face_detection = self.mp_face.FaceDetection(
                model_selection=1, 
                min_detection_confidence=0.5
            )
            
    def cleanup_clips(self, clips):
        """Properly close all clips to prevent process handle errors"""
        for clip in clips:
            try:
                if hasattr(clip, 'audio') and clip.audio:
                    clip.audio.close()
                clip.close()
            except:
                pass
            
    def create_clips_from_moments(self, video_path: str, key_moments: List[KeyMoment]) -> List[VideoFileClip]:
        """Create video clips from key moments with transitions"""
        clips = []
        
        print(f"Creating clips from {len(key_moments)} key moments...")
        
        for i, moment in enumerate(key_moments):
            try:
                # Load the specific segment
                clip = VideoFileClip(video_path).subclip(moment.start, moment.end)
                
                # Add fade transitions
                if i == 0:
                    clip = clip.fadein(Config.FADE_DURATION)
                if i == len(key_moments) - 1:
                    clip = clip.fadeout(Config.FADE_DURATION)
                
                clips.append(clip)
                print(f"  Created clip {i+1}/{len(key_moments)}: {moment.start:.1f}s - {moment.end:.1f}s")
                
            except Exception as e:
                print(f"  Error creating clip {i+1}: {e}")
                continue
        
        return clips
    
    def add_transitions(self, clips: List[VideoFileClip]) -> VideoFileClip:
        """Add professional transitions between clips"""
        if len(clips) <= 1:
            return clips[0] if clips else None
        
        # Create crossfade transitions
        final_clips = [clips[0]]
        
        for i in range(1, len(clips)):
            # Add crossfade transition
            prev_clip = final_clips[-1]
            current_clip = clips[i]
            
            # Crossfade the last portion of previous clip with beginning of current clip
            transition_duration = min(Config.TRANSITION_DURATION, 
                                    prev_clip.duration * 0.3, 
                                    current_clip.duration * 0.3)
            
            if transition_duration > 0.1:
                # Create crossfade effect
                prev_part = prev_clip.subclip(0, prev_clip.duration - transition_duration/2)
                transition_part1 = prev_clip.subclip(prev_clip.duration - transition_duration/2).fadeout(transition_duration/2)
                transition_part2 = current_clip.subclip(0, transition_duration/2).fadein(transition_duration/2)
                current_part = current_clip.subclip(transition_duration/2)
                
                # Replace last clip with parts
                final_clips[-1] = prev_part
                final_clips.extend([
                    CompositeVideoClip([transition_part1, transition_part2]),
                    current_part
                ])
            else:
                final_clips.append(current_clip)
        
        return concatenate_videoclips(final_clips, method="compose")
    
    def add_background_music(self, video_clip: VideoFileClip) -> VideoFileClip:
        """Add background music to video"""
        if not os.path.exists(Config.MUSIC_FOLDER):
            print(f"Music folder {Config.MUSIC_FOLDER} not found")
            return video_clip
        
        music_files = [f for f in os.listdir(Config.MUSIC_FOLDER) 
                      if f.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg'))]
        
        if not music_files:
            print("No music files found")
            return video_clip
        
        # Select random background music
        music_file = random.choice(music_files)
        music_path = os.path.join(Config.MUSIC_FOLDER, music_file)
        
        try:
            with AudioFileClip(music_path) as music:
                # Adjust music duration to match video
                if music.duration > video_clip.duration:
                    start_time = random.uniform(0, music.duration - video_clip.duration)
                    music_segment = music.subclip(start_time, start_time + video_clip.duration)
                elif music.duration < video_clip.duration:
                    music_segment = music.fx(afx.audio_loop, duration=video_clip.duration)
                else:
                    music_segment = music
                
                # Set background music volume
                music_segment = music_segment.fx(afx.volumex, 0.15)
                
                # Combine audio
                if video_clip.audio:
                    final_audio = CompositeAudioClip([video_clip.audio, music_segment])
                else:
                    final_audio = music_segment
                
                return video_clip.set_audio(final_audio)
            
        except Exception as e:
            print(f"Error adding background music: {e}")
            return video_clip
    
    def create_subtitles(self, key_moments: List[KeyMoment], video_duration: float) -> List[TextClip]:
        """Create styled subtitle clips"""
        subtitle_clips = []
        current_time = 0
        
        font_path = os.path.join(Config.FONTS_DIR, "Roboto_Condensed-Black.ttf")
        if not os.path.exists(font_path):
            font_path = None  # Use default font
            print("Font not found, using default")
        
        for moment in key_moments:
            # Split long text into multiple lines
            lines = textwrap.wrap(moment.text, width=30)
            
            for line in lines:
                try:
                    subtitle = TextClip(
                        line,
                        fontsize=40,
                        color='white',
                        font=font_path,
                        stroke_color='black',
                        stroke_width=2,
                        method='caption'
                    ).set_duration(min(3.0, video_duration - current_time))
                    
                    subtitle = subtitle.set_start(current_time).set_position(('center', 'bottom'))
                    subtitle_clips.append(subtitle)
                    current_time += 2.5  # Stagger subtitle timings
                    
                except Exception as e:
                    print(f"Error creating subtitle: {e}")
                    continue
        
        return subtitle_clips
    
    def blur_faces(self, clip: VideoFileClip) -> VideoFileClip:
        """Add face blur for privacy"""
        self.load_face_detection()
        
        def process_frame(frame):
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(rgb_frame)
            
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    # Expand bbox for better coverage
                    expand = 0.2
                    x = max(0, int(x - width * expand))
                    y = max(0, int(y - height * expand))
                    width = min(w - x, int(width * (1 + 2 * expand)))
                    height = min(h - y, int(height * (1 + 2 * expand)))
                    
                    # Apply blur
                    roi = frame[y:y+height, x:x+width]
                    if roi.size > 0:
                        blurred_roi = cv2.GaussianBlur(roi, (51, 51), 0)
                        frame[y:y+height, x:x+width] = blurred_roi
            
            return frame
        
        return clip.fl_image(process_frame)

# =========================
# Main Speaker Short Maker
# =========================

class SpeakerShortMaker:
    def __init__(self):
        self.downloader = VideoDownloader()
        self.speech_processor = SpeechProcessor()
        self.video_processor = VideoProcessor()
        
        # Create output directory
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
                # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)
        
        # Create output directory
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

    def _cleanup_on_exit(self):
        """Cleanup resources on program exit"""
        try:
            # Force garbage collection
            import gc
            gc.collect()
        except:
            pass
    
    def create_short_video(self,
                          url: str = None,
                          local_path: str = None,
                          output_name: str = None,
                          blur_faces: bool = False,
                          language: str = None,
                          whisper_model: str = "small") -> str:
        """Main function to create short video from speaker content"""

        try:
            # Step 1: Get video path (download or use local)
            if local_path:
                print(f"Using local video: {local_path}")
                if not os.path.isfile(local_path):
                    raise Exception(f"Local video file not found: {local_path}")
                video_path = local_path
            elif url:
                print(f"Downloading video from: {url}")
                video_path = self.downloader.download_video(url)
                print(f"Downloaded to: {video_path}")
            else:
                raise Exception("Either URL or local path must be provided")
            
            # Step 2: Transcribe speech
            print("Transcribing speech...")
            self.speech_processor.model_size = whisper_model
            segments = self.speech_processor.transcribe_video(video_path, language)
            
            if not segments:
                raise Exception("No speech detected in video")
            
            # Step 3: Identify key moments
            print("Analyzing key moments...")
            key_moments = self.speech_processor.analyze_key_moments(segments)
            
            if not key_moments:
                raise Exception("No key moments identified")
            
            print(f"Selected {len(key_moments)} key moments")
            
            # Step 4: Create clips from key moments
            print("Creating video clips...")
            clips = self.video_processor.create_clips_from_moments(video_path, key_moments)
            
            if not clips:
                raise Exception("Failed to create video clips")
            
            # Step 5: Add transitions
            print("Adding transitions...")
            final_video = self.video_processor.add_transitions(clips)
            
            # Step 6: Ensure under 60 seconds
            if final_video.duration > Config.MAX_DURATION:
                print(f"Video too long ({final_video.duration:.1f}s), trimming to {Config.MAX_DURATION}s")
                final_video = final_video.subclip(0, Config.MAX_DURATION)
            
            # Step 7: Add face blur if requested
            if blur_faces:
                print("Adding face blur...")
                final_video = self.video_processor.blur_faces(final_video)
            
            # Step 8: Add background music
            print("Adding background music...")
            final_video = self.video_processor.add_background_music(final_video)
            
            # Step 9: Add subtitles
            print("Creating subtitles...")
            subtitle_clips = self.video_processor.create_subtitles(key_moments, final_video.duration)
            
            if subtitle_clips:
                final_video = CompositeVideoClip([final_video] + subtitle_clips)
            
            # Step 10: Export final video
            if output_name is None:
                output_name = f"speaker_short_{int(time.time())}.mp4"
            
            output_path = os.path.join(Config.OUTPUT_DIR, output_name)
            
            print(f"Exporting final video to: {output_path}")
            
            final_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                ffmpeg_params=['-crf', '18']
            )
            
            # Cleanup
            for clip in clips:
                clip.close()
            final_video.close()
            
            self.video_processor.cleanup_clips(clips)

            if subtitle_clips:
                for sub_clip in subtitle_clips:
                    try:
                        sub_clip.close()
                    except:
                        pass

            try:
                final_video.close()
            except:
                pass

            # Also close the original video file
            try:
                original_video = VideoFileClip(video_path)
                original_video.close()
            except:
                pass
                
                print(f"✅ Short video created successfully: {output_path}")
                return output_path
            
        except Exception as e:
            print(f"❌ Error creating short video: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Speaker Short Video Maker")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=str, help="Path to local video file")
    src.add_argument("--url", type=str, help="Video URL to download and process")
    parser.add_argument("--output", "-o", help="Output filename")
    parser.add_argument("--blur-faces", action="store_true", help="Blur faces for privacy")
    parser.add_argument("--language", "-l", help="Force language for transcription (e.g., en, es, fr)")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper model size")
    parser.add_argument("--no-music", action="store_true", help="Don't add background music")
    
    args = parser.parse_args()
    
    try:
        maker = SpeakerShortMaker()
        
        # Disable background music if requested
        if args.no_music:
            Config.MUSIC_FOLDER = ""
        
        output_path = maker.create_short_video(
            url=args.url if hasattr(args, 'url') and args.url else None,
            local_path=args.input if hasattr(args, 'input') and args.input else None,
            output_name=args.output,
            blur_faces=args.blur_faces,
            language=args.language,
            whisper_model=args.whisper_model
        )
        
        print(f"\n🎉 Success! Your speaker short video is ready: {output_path}")
        
        
    except Exception as e:
        print(f"\n💥 Failed to create video: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
