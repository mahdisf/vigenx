"""Twitch clip finder — discovers clips by game, view count, and date range."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv  # type: ignore[import]

from sources.twitch_downloader import download_twitch_vod

log = logging.getLogger(__name__)

load_dotenv()

GAME_NAME = "Counter-Strike"
MIN_VIEWS = 200
DAYS_BACK = 7
OUTPUT_DIR = "clips"


async def setup_twitch(client_id: str, client_secret: str):
    from twitchAPI.twitch import Twitch  # type: ignore[import]

    twitch = Twitch(client_id, client_secret)
    await twitch.authenticate_app([])
    return twitch


async def get_game_id(twitch, game_name: str) -> str | None:
    log.info("Searching for exact Twitch category match: '%s'", game_name)
    try:
        async for game in twitch.search_categories(query=game_name):
            if game.name.lower() == game_name.lower():
                log.info("Found: %s (ID: %s)", game.name, game.id)
                return game.id
    except Exception as exc:
        log.error("Error searching for game ID: %s", exc)
    log.warning("No exact match found for '%s'", game_name)
    return None


async def get_valuable_clips(
    twitch,
    game_id: str,
    min_views: int = 100,
    days_back: int = 7,
) -> list:
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days_back)
    clips = []
    async for clip in twitch.get_clips(
        game_id=game_id, first=20, started_at=start_time, ended_at=end_time
    ):
        if clip.view_count >= min_views:
            clips.append(clip)
    return clips


async def _main(
    game_name: str = GAME_NAME,
    min_views: int = MIN_VIEWS,
    days_back: int = DAYS_BACK,
    output_dir: str = OUTPUT_DIR,
) -> None:
    client_id = os.environ.get("TWITCH_CLIENT_ID", "")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        log.error("TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET must be set in environment.")
        return

    os.makedirs(output_dir, exist_ok=True)
    twitch = await setup_twitch(client_id, client_secret)

    game_id = await get_game_id(twitch, game_name)
    if not game_id:
        log.error("Could not find game '%s'. Exiting.", game_name)
        await twitch.close()
        return

    clips = await get_valuable_clips(twitch, game_id=game_id, min_views=min_views, days_back=days_back)
    log.info("Found %d clips with >= %d views", len(clips), min_views)

    for clip in clips:
        log.info("Downloading clip '%s' (%d views)", clip.title, clip.view_count)
        try:
            download_twitch_vod(url=clip.url, output_dir=output_dir, game_name=game_name)
        except Exception as exc:
            log.error("Failed to download clip %s: %s", clip.id, exc)

    await twitch.close()


if __name__ == "__main__":
    from core.logging_setup import configure_logging
    configure_logging()
    asyncio.run(_main())
