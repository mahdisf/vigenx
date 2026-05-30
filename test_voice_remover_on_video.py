# test_voice_remover_on_video.py

import os
import tempfile
import shutil
from moviepy.editor import VideoFileClip, AudioFileClip
from voice_remover import separate_vocals_with_demucs

# --- CONFIGURATION ---
# 1. SET THE PATH TO YOUR INPUT VIDEO
INPUT_VIDEO_PATH = "./downloads/Counter-Strike-2.mp4" 

# 2. SET THE DESIRED NAME FOR THE OUTPUT VIDEO
OUTPUT_VIDEO_PATH = "./test_output_no_vocals.mp4"
# --- END CONFIGURATION ---


def test_separation(video_path: str, output_path: str):
    """
    Takes a video, removes vocals from its audio, and saves a new video.
    """
    if not os.path.exists(video_path):
        print(f"Error: Input video not found at '{video_path}'")
        return

    print(f"Loading video: {video_path}")
    video = VideoFileClip(video_path)

    if video.audio is None:
        print("Error: The video has no audio track.")
        return

    # Create a temporary directory to store intermediate files
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")

    try:
        # 1. Extract original audio to a temporary file
        original_audio_path = os.path.join(temp_dir, "original_audio.mp3")
        print("Extracting original audio...")
        video.audio.write_audiofile(original_audio_path, logger=None)

        # 2. Run the vocal remover function
        # This is the critical step we are testing.
        print("\n--- Running Demucs Vocal Separation ---")
        separation_result = separate_vocals_with_demucs(original_audio_path, temp_dir)

        # 3. Check the result
        if "error" in separation_result:
            print("\n--- VOCAL SEPARATION FAILED! ---")
            print("Error message from Demucs:")
            print(separation_result["error"])
            print("------------------------------------")
            return

        print("\n--- Vocal Separation Successful! ---")
        no_vocals_file = separation_result["no_vocals"]
        print(f"Instrumental track saved to: {no_vocals_file}")

        # 4. Create a new audio clip from the instrumental track
        instrumental_audio = AudioFileClip(no_vocals_file)

        # 5. Set the new audio on the original video
        print("Attaching new audio to the video...")
        final_video = video.set_audio(instrumental_audio)

        # 6. Write the final video file
        print(f"Saving final video to: {output_path}")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        print("\n✅ Test complete! Check the output file.")

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        # Clean up the temporary directory and all its contents
        print(f"Cleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir)
        video.close()


if __name__ == "__main__":
    test_separation(INPUT_VIDEO_PATH, OUTPUT_VIDEO_PATH)