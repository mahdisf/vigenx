from twitch_video_downloader import download_twitch_vod, get_next_processed_video_id, _download_single_video
from gemini_client import generate_text
from vocal_separator import separate_vocals_with_demucs

import ast    
import textwrap    
from text_to_speech import text_to_speech
import os
import random
import cv2
import numpy as np
from moviepy.editor import *
from pydub import AudioSegment
import tempfile
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
from wand.image import Image as WandImage
from wand.drawing import Drawing
from wand.color import Color
from moviepy.editor import VideoFileClip
from moviepy.editor import TextClip
from moviepy.audio.fx import all as afx
import shutil
from moviepy.config import change_settings
# Set the full path to your ImageMagick magick.exe
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})



# Configuration
INPUT_DIR = "downloads"
OUTPUT_DIR = "output"
GAME_NAME = "Counter-Strike"  # Change this to your video name (without extension)
VIDEO_ID , VIDEO_TITLE = get_next_processed_video_id(OUTPUT_DIR,GAME_NAME,Auto=False)      # Change this to your video ID
MUSIC_FOLDER = "./musics"
OUTPUT_VIDEO = f"./{OUTPUT_DIR}/{GAME_NAME}-{VIDEO_ID}_processed.mp4"

print(f"Processing video ID: {VIDEO_ID}, Title: {VIDEO_TITLE}")

URL = 0 #"https://www.twitch.tv/rekellus/videos?filter=highlights&sort=time"  # Replace with your Twitch VOD URL
# --- Download from Twitch.

if URL:
    try:
        download_twitch_vod(URL, INPUT_DIR, game_name= GAME_NAME, quiet=False)
        print("list of videos Downloaded successfully")
    except:
        print("single video started to Download ...")
        _download_single_video(URL, INPUT_DIR, game_name= GAME_NAME, quiet=False)
        print("single video Downloaded successfully")

INPUT_VIDEO = f"./{INPUT_DIR}/{GAME_NAME}-{VIDEO_ID}.mp4"
    

# Create output directory if it doesn't exist
os.makedirs("./output", exist_ok=True)

class VideoProcessor:
    def __init__(self):
        self.video = None
        self.audio = None
        self.music = None
        self.model = None
        
    def load_yolo_model(self):
        """Load YOLO model for object detection"""
        try:
            self.model = YOLO('yolov8n.pt')  # Download if not exists
            print("YOLO model loaded successfully")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            return False
        return True
    
    def detect_gun_in_frame(self, frame):
        """Detect gun in a frame and return bounding box"""
        if self.model is None:
            return None
            
        results = self.model(frame)
        
        # A practical, simplified list for custom YOLO training on Counter-Strike
        weapon_classes = ['gun', 'rifle', 'pistol', 'knife', 'grenade', 'c4-explosive', 'smg', 'sniper-rifle', 'shotgun']
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id].lower()
                    
                    if any(weapon in class_name for weapon in weapon_classes):
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        return (int(x1), int(y1), int(x2), int(y2))
        return None
    
    def find_gun_and_crop_region(self, video_path, Automate =True):
        """Find gun in video and determine crop region"""
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video at {video_path}")
            return None
        
        if Automate:
                    # --- KEY CHANGE: Get video dimensions ---
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # --- KEY CHANGE: Calculate the default 3/5 center crop ---
            # The crop starts after the first 1/5 of the width
            crop_left_default = int(video_width * (1/4))
            # The crop ends before the last 1/5 of the width (i.e., at the 4/5 mark)
            crop_right_default = int(video_width * (3/4))
            
            default_crop_region = (crop_left_default, 0, crop_right_default, video_height)

            print(f"Skipping gun detection, using center 3/5 crop: {default_crop_region}")
            cap.release()
            return default_crop_region
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Sample frames throughout the video
        sample_frames = np.linspace(0, frame_count-1, min(20, frame_count), dtype=int)
        
        gun_positions = []
        
        for frame_idx in sample_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue
                
            gun_bbox = self.detect_gun_in_frame(frame)
            if gun_bbox:
                gun_positions.append(gun_bbox)
        
        cap.release()
        
        if gun_positions:
            # Calculate average gun position
            avg_x = sum([pos[0] + pos[2] for pos in gun_positions]) // (2 * len(gun_positions))
            
            # Define crop region: 500 pixels left and right from gun center
            crop_left = max(0, avg_x - 500)
            crop_right = min(1920, avg_x + 500)  # Assuming max width
            
            return crop_left, 0, crop_right, 1080  # left, top, right, bottom
        else:
            print("No gun detected, using center crop")
            return 560, 0, 1360, 1080  # Center crop 1000px wide
    
    def get_random_music(self):
        """Get random music file from musics folder"""
        if not os.path.exists(MUSIC_FOLDER):
            print(f"Music folder {MUSIC_FOLDER} not found")
            return None
            
        music_files = [f for f in os.listdir(MUSIC_FOLDER) 
                      if f.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg'))]
        
        if not music_files:
            print("No music files found")
            return None
            
        selected_music = random.choice(music_files)
        return os.path.join(MUSIC_FOLDER, selected_music)
    
    def get_video_duration(self,video_path):
        """Simple function to get video duration - use this in your main script"""
        try:
            video = VideoFileClip(video_path)
            duration = video.duration
            video.close()
            return duration
        except:
            # Fallback to OpenCV
            try:
                cap = cv2.VideoCapture(video_path)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()
                return frame_count / fps if fps > 0 else None
            except:
                return None
            
    def get_gemini_comment(self):
        """Get funny comment from Gemini-text module"""
        self.duration = self.get_video_duration(INPUT_VIDEO)
        voice_duration = int(self.duration)/3
        try:
            # Import your Gemini client module here.
            gemini_output_string = generate_text(f"""
                                    You are a skilled female gamer preparing to share a highlight from your gameplay with your audience.
                                    At the beginning of the video, deliver a short, engaging introduction—no longer than {voice_duration} seconds—that captures attention
                                    and encourages viewers to watch the entire clip.the video title is {VIDEO_TITLE}, so you should say some thing related.
                                    don't use bold or any markdown formatting.don't use hashtags, *,/, or _.
                                    Focus on making it sound natural and relatable, as if you're chatting with friends.
                                    The tone should be emotionful, cool, confident, captivating, and tailored to hook your audience immediately.
                                    [Do not include any additional commentary beyond the intro.]
                                    your answer should be just a python dictionary with these elements:
                                    intro_voice : "text that you will say in the begging of video and duration is {voice_duration} second. related to title:{VIDEO_TITLE}"
                                    headline : "2 words text that you will write top of the video related to title"
                                    headline_emoji : "2 or 3 emojies (not more!) which are related to title"
                                    title : "enhanced title of video contain some emojies and engaging related text up to 7 words."
                                    discription : "some thing related + call to action subscribe me with this sub link: bit.ly/3Kb33oE"
                                    """)
            
            data_dict = ast.literal_eval(gemini_output_string)
            
            comment = data_dict['headline']  # The main title for the video
            emoji = data_dict['headline_emoji'] # The emojis for the headline
            during_voice = data_dict['intro_voice'] # The text for the voiceover
            
            return comment, emoji, self.duration , during_voice , data_dict['title'], data_dict['discription']
        
        except Exception as e:
            print(f"Error getting Gemini comment: {e}")
            comments = [
                "Epic fail! ",
                "So random! ",
                "Mind blown! ",
                "Pure gold! ",
                "What happened? ",
                "Absolutely crazy! "
            ]
            comment = random.choice(comments)
            emojies = [
                        "🤯🎯🔥",
                        "😂🤦💀",
                        "👑🏆🥇",
                        "😱‼️💥",
                        "🧠♟️👑",
                        "🤪🍌🤣",
                        "💪💯✨",
                        "💎🎁🎉",
                        "⚔️🔥🏆",
                        "⚡️🎯🤯",
                        "🤓💡🏆",
                        "🤡💣💥",
                        "🚀📈💯",
                        "👀👻😱",
                        "🤣🎮🔥",
                        "🤔🗺️🎯",
                        "💥🚁💀",
                        "😮💎✨",
                        "🤦🕹️🗑️",
                        "🔪🥷💀",
                        "😤🎮💯",
                        "✨🎁👑",
                        "😂🎯💥",
                        "📈🏆🎉"
                    ]
            emoji = random.choice(emojies)
            
            return comment, emoji, self.duration , during_voice
    
    def text_to_speech(self, text, output_path):
        """Convert text to speech using female voice"""
        try:
            tts = text_to_speech(text=text, file_path=output_path)
                        
            audio = AudioSegment.from_file(output_path)
            return audio.duration_seconds
        
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
            return False
        
    def split_text(self,text, max_chars=13):
        """Split long text into smaller lines for subtitles"""
        return textwrap.wrap(text, width=max_chars)

    
    def create_text_clip(self, text ,emoji, duration, fontsize=60, color='white'):
        """Create text clip with Wand for colorful emojis"""
        width, height = 1080, 200
        image = Image.new('RGBA', (width, height))
        
        # Create a drawing context
        draw = ImageDraw.Draw(image)
        text_font_path = "./fonts/Roboto_Condensed-Black.ttf" 
        
        try:
            text_font = ImageFont.truetype(text_font_path, fontsize)
            print(f"Loaded font: {text_font_path}")
        except Exception as e:
            text_font = ImageFont.load_default()
            print(f"Error loading font {text_font_path}: {e}. Using default font.")
        
            # Try to find an emoji font for colorful emojis
        emoji_font = None
        emoji_font_paths = [
            # Windows
            "C:/Windows/Fonts/seguiemj.ttf",  # Segoe UI Emoji
            # macOS
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            # Linux
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        ]
        
        for emoji_path in emoji_font_paths:
            if os.path.exists(emoji_path):
                try:
                    emoji_font = ImageFont.truetype(emoji_path, fontsize)
                    print(f"Loaded emoji font: {emoji_path}")
                    break
                except:
                    continue
        
        # Calculate positions for text and emojis
        text_bbox = draw.textbbox((0, 0), text, font=text_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        emoji_bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
        emoji_width = emoji_bbox[2] - emoji_bbox[0]
        emoji_height = emoji_bbox[3] - emoji_bbox[1]
        
        total_width = text_width + emoji_width
        max_height = max(text_height, emoji_height)
        
        # Center the combined text and emojis
        start_x = (width - total_width) // 2
        text_y = (height - max_height) // 2
        
        # Draw the text part
        draw.text((start_x, text_y), text, font=text_font, fill=color,stroke_width=3, stroke_fill="#FD3C9D")
        
        # Draw the emoji part
        emoji_x = start_x + text_width
        draw.text((emoji_x, text_y+10), emoji, font=emoji_font, fill=color, embedded_color=True)
        
                
        # Save to temporary file
        temp_path = tempfile.mktemp(suffix='.png')
        image.save(temp_path)
        
        # Create ImageClip from the saved image
        from moviepy.editor import ImageClip
        clip = ImageClip(temp_path).set_duration(duration)
        
        # Clean up temp file
        os.remove(temp_path)
        
        return clip
    
    def create_subtitle_clips(self,text, audio_path, fontsize=80, color='white', size=(1000, None)):
        
            """Create a list of TextClips synced with audio"""
            audio = AudioSegment.from_file(audio_path)
            total_duration = audio.duration_seconds
            fontpath = './fonts/Roboto_Condensed-Black.ttf'
            lines = self.split_text(text)
            num_lines = len(lines)
            duration_per_line = total_duration / num_lines

            clips = []
            for line in lines:
                clip = TextClip(line, fontsize=fontsize, color=color, font=fontpath,stroke_width=3,
                                stroke_color="#FD3C9D", method='caption', size=size).set_duration(duration_per_line)
                
                clips.append(clip)
            
            # Combine text clips into one video clip
            subtitles = concatenate_videoclips(clips)
            # audio_clip = AudioFileClip(audio_path)
            # subtitles = subtitles.set_audio(audio_clip)
            return subtitles

    def save_title_and_description(self, title: str, description: str):
        """
        Saves a given title and description to a specified text file.

        The file will be overwritten if it already exists. The text is saved
        in a human-readable format with UTF-8 encoding.

        Args:
            title (str): The title to be saved.
            description (str): The description to be saved.
            filename (str): The path and name of the file to save the data to.
                            Example: 'video_details.txt'
        """
        filename = os.path.join(OUTPUT_DIR, f"{GAME_NAME}-{VIDEO_ID}_details.txt")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Title: {title}\n")
                f.write("-" * 20 + "\n")  # A separator for clarity
                f.write(f"Description: {description}\n")
            print(f"Successfully saved data to '{filename}'")
        except IOError as e:
            print(f"Error: Could not write to file '{filename}'. Reason: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    
    def process_video(self):
        """Main video processing function"""
        if not os.path.exists(INPUT_VIDEO):
            print(f"Input video {INPUT_VIDEO} not found!")
            return False
        
        print("Loading video...")
        video = VideoFileClip(INPUT_VIDEO)
        
        # Ensure video is maximum 59 seconds
        if video.duration > 59:
            print(f"Video too long ({video.duration}s), trimming to 59s from middle")
            start_time = (video.duration - 59) / 2
            video = video.subclip(start_time, start_time + 59)
        
        print("Separating vocals from background sound...")
        demucs_output_dir = None # To store the temp directory path for cleanup
        instrumental_audio = None

        if video.audio:
            # Create a temporary directory for demucs output
            demucs_output_dir = tempfile.mkdtemp()
            original_audio_path = os.path.join(demucs_output_dir, "original_audio.wav")

            try:
                # Write the original audio to a file
                video.audio.write_audiofile(original_audio_path, codec="pcm_s16le", fps=44100, logger=None)

                # Call the vocal remover function
                separation_result = separate_vocals_with_demucs(original_audio_path, demucs_output_dir)

                if "error" in separation_result:
                    print(f"Vocal separation failed: {separation_result['error']}. Removing all audio instead.")
                    video = video.without_audio()
                else:
                    print("Vocal separation successful. Using instrumental track.")
                    # Assign the clip to our variable, but DON'T set it on the video yet.
                    instrumental_audio = AudioFileClip(separation_result["no_vocals"])
                    
            except Exception as e:
                print(f"An error occurred during audio separation: {e}. Removing all audio.")
                video = video.without_audio()
        else:
            print("Video has no original audio to process.")
            video = video.without_audio()

        print("Preparing and composing audio tracks...")
        
        # 1. Create a list to hold all audio clips for this section
        audio_sources = []
        
        # 2. Add the instrumental track to the list if it exists
        if instrumental_audio:
            instrumental_audio = instrumental_audio.fx(afx.volumex, 0.7)
            audio_sources.append(instrumental_audio)
            

        # 3. Load, process, and add the background music if it exists
        music_file = self.get_random_music()
        if music_file:
            music = AudioFileClip(music_file)
            # Ensure music matches video duration
            if music.duration > video.duration:
                max_start_time = music.duration - video.duration
                start_time = random.uniform(0, max_start_time)
                music = music.subclip(start_time, start_time + video.duration)
            elif music.duration < video.duration:
                music = music.fx(afx.audio_loop, duration=video.duration)
            
            # Set volume and add to our list
            music = music.fx(afx.volumex, 0.1)
            audio_sources.append(music)
        
        # 4. If we have any audio sources, compose them in one step
        if audio_sources:
            print(f"Composing {len(audio_sources)} audio tracks (instrumental/music)...")
            # Create the final composite audio for this stage
            combined_audio = CompositeAudioClip(audio_sources)
            # Set this composed audio on the video clip
            video = video.set_audio(combined_audio)
        else:
            # If no audio sources were found, ensure the video is silent
            video = video.without_audio()            
        
        print("Detecting gun and cropping video...")
        if self.load_yolo_model():
            crop_coords = self.find_gun_and_crop_region(INPUT_VIDEO,Automate=True)
            print(f"Crop coordinates: {crop_coords}")
        else:
            # Fallback to center crop
            crop_coords = (560, 0, 1360, 1080)
        
        # Crop video
        audio_track = video.audio
        
        video = video.crop(x1=crop_coords[0], y1=crop_coords[1], # type: ignore
                          x2=crop_coords[2], y2=crop_coords[3]) # type: ignore
        
        video = video.set_audio(audio_track)
        
        print("Getting AI comment...")
        comment,emoji, comment_duration,comment_text , title , description = self.get_gemini_comment() # type: ignore
        
        self.save_title_and_description(title,description)
        
        print("Creating text-to-speech audio...")
        tts_path = tempfile.mktemp(suffix='.wav')
        if self.text_to_speech(comment_text, tts_path):
            tts_audio = AudioFileClip(tts_path, fps=44100)
            
            # Add TTS audio to video with a 1-second delay
            delayed_tts_audio = tts_audio.fx(afx.volumex,0.8).set_start(1.5)  # Start after 1.5 seconds

            if video.audio:
                # If there's background music, compose it with the delayed voiceover
                final_audio = CompositeAudioClip([video.audio, delayed_tts_audio])
            else:
                # If there's no music, we still use CompositeAudioClip to respect the start time
                final_audio = CompositeAudioClip([delayed_tts_audio])

            final_audio = final_audio.fx(afx.volumex, 0.9)
            temp_audio_path = tempfile.mktemp(suffix=".wav")
            final_audio.write_audiofile(temp_audio_path, codec="pcm_s16le", fps=44100, logger=None)

            # Reload as AudioFileClip → now you can fx it
            final_audio = AudioFileClip(temp_audio_path).fx(afx.audio_normalize)
            video = video.set_audio(final_audio)
        
        print("Adding text overlays...")
        # Top comment
        top_text = self.create_text_clip(comment, emoji,
                                       min(comment_duration, video.duration),fontsize=90)
        
        # Bottom subtitle 
        bottom_text = self.create_subtitle_clips(comment_text, tts_path,fontsize=90)
        
        # Create blurred background for vertical format
        print("Creating vertical format with blurred background...")
        
        # ... (previous code in your process_video function)

        print("Creating vertical format with blurred background...")
        
        # 1. Create the background by scaling the main video up to fill the vertical frame
        background = video.resize(height=1920)
        # Then, crop the resized video from its center to get a 1080x1920 clip
        background = background.crop(x_center=background.w/2, y_center=background.h/2, width=1080, height=1920)
        
        # 2. Apply a blur effect using OpenCV
        # We use fl_image to apply a function to each frame of the clip.
        # cv2.GaussianBlur is the function that applies the blur.
        # You can increase the (25, 25) kernel size for more blur, e.g., (51, 51).
        background = background.fl_image(lambda frame: cv2.GaussianBlur(frame, (25, 25), 0))
        
        # Resize the main video to fill the full width of the screen (1080 pixels)
        video = video.resize(width=1080)    
        # 3. Composite the final video
        # We place the blurred background first, then the original gameplay video on top.
        # I have corrected 'video_resized' to 'video' here.
        final_video = CompositeVideoClip([
            background,
            video.set_position('center'), # The original, un-blurred gameplay clip
            top_text.set_position(('center', 200)), 
            bottom_text.set_start(1.5).set_position(('center', 1400)) 
        ])
        
        fadein_duration = 0.5
        fadeout_duration = 2
        
        final_video = final_video.fadeout(fadeout_duration)
        final_video = final_video.fadein(fadein_duration)
        
        # This will only work if the video has an audio track
        if video.audio:
            final_video = final_video.fx(afx.audio_fadein, fadein_duration)
            final_video = final_video.fx(afx.audio_fadeout, fadeout_duration)
        
        print(f"Saving final video to {OUTPUT_VIDEO}...")
        
        final_video.write_videofile(
            OUTPUT_VIDEO,
            fps=30,
            codec='h264_nvenc',   # GPU-accelerated encoding
            audio_codec='aac',
            preset='medium',        # optional, speed/quality tradeoff
            ffmpeg_params=['-rc:v', 'vbr', '-cq:v', '18']  # optional quality settings
        )
                
        # Cleanup
        video.close()
        if music_file:
            music.close()

        if os.path.exists(tts_path):
            os.remove(tts_path)
            
        if demucs_output_dir and os.path.exists(demucs_output_dir):
            shutil.rmtree(demucs_output_dir)
        
        print("Video processing completed!")
        return True

def main():
    processor = VideoProcessor()
    success = processor.process_video()
    
    if success:
        print(f"✅ Processing completed! Output saved to: {OUTPUT_VIDEO}")
    else:
        print("❌ Processing failed!")

if __name__ == "__main__":
    main()
