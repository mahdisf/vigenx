import os
from twitchAPI.twitch import Twitch
import asyncio
from twitch_video_downloader import download_twitch_vod
from datetime import datetime, timedelta
from dotenv import load_dotenv


load_dotenv()  # Load variables from .env file
if 'TWITCH_CLIENT_ID':
    print('TWITCH_CLIENT_ID set correctly!')
else:
    print('TWITCH_CLIENT_SECRET has problem!!')

# Twitch API setup
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')  # Set in environment
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')  # Set in environment

# Configuration
GAME_NAME = "Counter-Strike"
MIN_VIEWS = 200  # Let's look for more popular clips
DAYS_BACK = 7
OUTPUT_DIR = "clips"  # Directory to save clips

async def setup_twitch():
    """Initialize and authenticate Twitch API client."""
    twitch = Twitch(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)
    await twitch.authenticate_app([])  # Await the async authentication
    return twitch

async def get_game_id(twitch: Twitch, game_name: str) -> str | None:
    """Search for the game ID for a given game name, requiring an exact match."""
    print(f"Searching for an exact match for game category '{game_name}'...")
    try:
        # Search for the category
        async for game in twitch.search_categories(query=game_name):
            # Check for an exact, case-insensitive match
            if game.name.lower() == game_name.lower():
                print(f"Found exact match: {game.name} with ID: {game.id}")
                return game.id
        
        # If the loop finishes without finding an exact match
        print(f"No exact match found for '{game_name}'. Please check the name on Twitch.")
        return None
            
    except Exception as e:
        print(f"An error occurred while searching for the game ID: {e}")
        return None

async def get_valuable_clips(twitch, game_id="21779", min_views=100, days_back=7):
    """Fetch valuable clips based on criteria."""
    # Calculate time range (last 7 days)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days_back)
    
    # Query clips for the game (returns an async generator)
    clips_gen = twitch.get_clips(
        game_id=game_id,
        first=20,  # Max 20 clips per request
        started_at=start_time,
        ended_at=end_time
    )
    
    # Collect clips that meet the view count criteria
    valuable_clips = []
    async for clip in clips_gen:  # Iterate over async generator
        if clip.view_count >= min_views:
            valuable_clips.append(clip)
    
    return valuable_clips

async def main():
    """Main function to find and download valuable clips."""
    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Initialize Twitch API
    twitch = await setup_twitch()
    
        # Get the Game ID
    game_id = await get_game_id(twitch, GAME_NAME)

    if not game_id:
        print(f"Could not find a game named '{GAME_NAME}'. Exiting.")
        await twitch.close()
        return
    
    # Find valuable clips (e.g., Fortnite, >100 views, last 7 days)
    clips = await get_valuable_clips(twitch, game_id=game_id, min_views=MIN_VIEWS, days_back=DAYS_BACK)
    
    # Download each clip
    for clip in clips:
        clip_id = clip.id
        
        print(f"--> Found valuable clip '{clip.title}' with {clip.view_count} views.")

        clip_url = clip.url 
        output_path = os.path.join(OUTPUT_DIR, f"{clip_id}.mp4")
        print(f"Attempting to download clip {clip_id}...")
        try:
            download_twitch_vod(url=clip_url, output_dir=OUTPUT_DIR, game_name=GAME_NAME)  # Call external download function
            print(f"Downloaded {clip_id} to {output_path}")
        except Exception as e:
            print(f"Failed to download {clip_id}: {e}")
    
    # Close the Twitch session to avoid warnings
    await twitch.close()

if __name__ == "__main__":
    asyncio.run(main())  # Run the async main function
