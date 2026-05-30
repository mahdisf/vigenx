import os
import sys
import yt_dlp

# --- HELPER FUNCTIONS (Mostly unchanged) ---

def is_video_downloaded(video_id, history_file):
    """Checks if a video ID exists in the download history file."""
    if not os.path.exists(history_file):
        return False
    with open(history_file, 'r') as f:
        downloaded_ids = {line.strip() for line in f}
    return video_id in downloaded_ids

def log_downloaded_video(video_id, history_file):
    """Appends a new video ID to the download history file."""
    with open(history_file, 'a') as f:
        f.write(f"{video_id}\n")

def get_next_video_id(output_dir, game_name):
    """Scans for the highest existing ID for a game and returns the next one."""
    max_id = 0
    if not os.path.exists(output_dir):
        return 1
    for filename in os.listdir(output_dir):
        if filename.startswith(f"{game_name}-") and filename.endswith(".mp4"):
            # A more robust way to extract the number
            base_name = filename[:-4] # Remove .mp4
            parts = base_name.split('-')
            if len(parts) > 1:
                try:
                    video_id = int(parts[-1])
                    if video_id > max_id:
                        max_id = video_id
                except ValueError:
                    continue
    return max_id + 1

# I've kept your custom function here as you might need it elsewhere
import os

def get_next_processed_video_id(output_dir, game_name, Auto=True):
    """
    Determines the next video ID to process.

    If Auto is True, it scans for the highest existing ID in files
    ending with '_processed.mp4' and returns the next sequential ID.
    The video title will be None.

    If Auto is False, it reads 'selected_videos.txt' from the output directory.
    The file should be formatted as: ID,"video title". It finds the first
    video in this list that does not have a corresponding '_processed.mp4'
    file and returns its ID and title.

    Args:
        output_dir (str): The directory where videos are stored.
        game_name (str): The base name for video files (e.g., 'Counter-Strike').
        Auto (bool): Flag to determine the mode of operation.

    Returns:
        tuple: A tuple containing (next_video_id, video_title).
               - In Auto=True mode, video_title is always None.
               - In Auto=False mode, returns (None, None) if 'selected_videos.txt'
                 is not found or if all listed videos are already processed.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if Auto:
        max_id = 0
        for filename in os.listdir(output_dir):
            if filename.startswith(f"{game_name}-") and filename.endswith("_processed.mp4"):
                base_name = filename[:-14]  # Remove _processed.mp4
                parts = base_name.split('-')
                if len(parts) > 1:
                    try:
                        video_id = int(parts[-1])
                        if video_id > max_id:
                            max_id = video_id
                    except ValueError:
                        continue
        return max_id + 1, None
    else:  # Auto is False
        selection_file = os.path.join(output_dir, "selected_videos.txt")
        if not os.path.exists(selection_file):
            print(f"Error: 'selected_videos.txt' not found in '{output_dir}'. Cannot proceed in manual mode.")
            return None, None

        with open(selection_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Split only on the first comma to handle titles with commas
                    id_str, title_part = line.split(',', 1)
                    video_id_to_check = int(id_str.strip())
                    # Strip whitespace and quotes from the title
                    video_title = title_part.strip()

                    # Check if the corresponding processed video already exists
                    processed_filename = f"{game_name}-{video_id_to_check}_processed.mp4"
                    if not os.path.exists(os.path.join(output_dir, processed_filename)):
                        # This is the next video to be processed
                        return video_id_to_check, video_title

                except (ValueError, IndexError):
                    print(f"Warning: Skipping malformed line in 'selected_videos.txt': {line}")
                    continue

        # If we get here, all videos in the list have been processed
        print("All videos listed in 'selected_videos.txt' have already been processed.")
        return None, None
    
def get_video_entries(url):
    """
    Uses yt-dlp to get a list of video entries from a URL.
    Handles both single video URLs and playlist URLs.
    """
    print("Fetching video/playlist metadata...")
    try:
        ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            print(f"Playlist detected with {len(info['entries'])} videos.")
            return info['entries']
        else:
            print("Single video detected.")
            return [info]
    except Exception as e:
        print(f"Error: Could not fetch video info. {e}")
        return []

def _download_single_video(url, output_path, quiet=True):
    """Private helper to download a single video URL to a specific path."""
    ydl_opts = {
        "format": "best",
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "quiet": quiet,
        "noplaylist": True, # Ensure we only ever download one video here
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"\nAn error occurred during download for {url}: {e}")
        return False

# --- THE NEW MAIN FUNCTION ---
def download_twitch_vod(url, output_dir, game_name, quiet=False):
    """
    Downloads new videos from a Twitch URL (single VOD or playlist).
    
    Checks for duplicates using a history file and names new videos sequentially.

    Args:
        url (str): The URL of the Twitch VOD or playlist.
        output_dir (str): The directory to save videos and the history log.
        game_name (str): The base name for the output video files.
        quiet (bool): Suppresses yt-dlp console output.

    Returns:
        list: A list of full file paths for all newly downloaded videos.
              Returns an empty list if no new videos were downloaded.
    """
    os.makedirs(output_dir, exist_ok=True)
    history_file = os.path.join(output_dir, "download_history.txt")
    
    video_entries = get_video_entries(url)
    if not video_entries:
        return [] # Return empty list if we couldn't get video info

    downloaded_files = []
    
    for i, video_info in enumerate(video_entries, 1):
        twitch_video_id = video_info.get('id')
        video_url = video_info.get('url')
        video_title = video_info.get('title', 'Untitled')

        print(f"\n--- [{i}/{len(video_entries)}] Processing: {video_title} (ID: {twitch_video_id}) ---")
        
        if is_video_downloaded(twitch_video_id, history_file):
            print("This video has already been downloaded. Skipping.")
            continue

        print("Video is new. Preparing to download...")
        next_id = get_next_video_id(output_dir, game_name)
        new_filename = f"{game_name}-{next_id}.mp4"
        output_path = os.path.join(output_dir, new_filename)
        
        print(f"Attempting to save as: {output_path}")

        success = _download_single_video(video_url, output_path, quiet)
        
        if success:
            print(f"Successfully downloaded: {new_filename}")
            log_downloaded_video(twitch_video_id, history_file)
            downloaded_files.append(output_path)
        else:
            print(f"Failed to download video: {video_title}")
            
    return downloaded_files

# --- SIMPLIFIED MAIN BLOCK FOR COMMAND-LINE USE ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python your_script_name.py <Twitch VOD or Playlist URL>")
        sys.exit(1)

    twitch_url_from_cli = sys.argv[1]
    output_directory = "downloads"

    game_name_from_cli = "Counter-Strike"
    if not game_name_from_cli:
        print("Error: Game name cannot be empty.")
        sys.exit(1)

    # Call the main function
    newly_downloaded_videos = download_twitch_vod(
        url=twitch_url_from_cli,
        output_dir=output_directory,
        game_name=game_name_from_cli
    )

    print("\n--- All tasks complete ---")
    if newly_downloaded_videos:
        print(f"Successfully downloaded {len(newly_downloaded_videos)} new video(s):")
        for filepath in newly_downloaded_videos:
            print(f" - {filepath}")
    else:
        print("No new videos were downloaded.")