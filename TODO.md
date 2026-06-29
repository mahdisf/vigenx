# TODO

## Immediate Code Work

- [x] Add argparse CLI to `pipelines/game_pipeline.py` — game name, source video, output path, URL, music folder, auto/manual mode.
- [x] Implement `config/` package with `AppConfig` dataclass and `default_config.toml` — replaces all top-of-file constants in every script.
- [x] Add a rights manifest JSON for every generated video: source URL, source owner, permission/license, music license, AI tools used, and transformation notes.
- [ ] Replace the simple speaker key-moment heuristic in `pipelines/speaker_pipeline.py` with a scoring layer that considers transcript, laughter/emotion, scene changes, audio spikes, and user-configured duration.
- [x] Make Gemini commentary in `core/gemini_client.py` return strict JSON via Pydantic schema and validate it before editing.
- [x] Add Flask review queue (`web/routes/review.py`) — show preview, rights checklist, approve/reject before any upload step.
- [x] Add structured output metadata next to every video: title, description, tags, timestamps, source info, policy checklist, and render settings.
- [x] Colorful text overlays — configurable `text_color` and `text_stroke_color` in `AppConfig` and `default_config.toml`.
- [x] Text drop-shadow — `text_shadow`, `text_shadow_color`, `text_shadow_offset` fields; rendered in `game_pipeline._create_text_clip()`.
- [x] Viewer-reaction style titles — Gemini prompt updated: titles read as other viewers praising the play, not the player self-promoting (e.g. "Nobody Saw That Coming 😱").
- [x] Gemini full title generation from video — `core/gemini_client.generate_title_from_video()` uploads and analyzes the video, returns a viewer-reaction title.
- [x] Scalable history spreadsheet — `core/history.py` appends one CSV row per run to `output/history.csv` (date, pipeline, game, video_id, title, paths, status).
- [x] Automated cover/thumbnail — `core/thumbnail.py` extracts a frame with ffmpeg and overlays a title bar with Pillow; called from game pipeline after export.
- [x] Logo overlay — `core/video_utils.add_logo_overlay()` composites a PNG logo at configurable position, opacity, and scale.
- [x] Intro/outro clips — `core/video_utils.prepend_append_clips()` concatenates intro/outro MP4s around the main clip; configured via `intro_clip` / `outro_clip` in AppConfig.
- [x] Video color filters — `core/video_utils.apply_color_filter()` applies brightness, contrast, and saturation adjustments; defaults are 1.0/1.0/1.1.
- [x] YAML config support — `config/settings.py load_config()` now accepts `.yaml` / `.yml` files in addition to TOML.

## MVP Pipeline

- [x] Input: accept local file, Twitch VOD/clip URL, or a vetted source list.
- [ ] Rights gate: reject sources without clear permission, public-domain status, or commercial license.
- [x] Download: save source video and source metadata.
- [x] Analyze: transcribe with Whisper, detect scenes/silence, and score highlight candidates.
- [x] Edit: trim selected moments, convert to vertical format, add subtitles, commentary/TTS, music, and optional face blur.
- [x] Review: show preview plus rights/monetization checklist in Flask web UI.
- [x] Export: write final MP4 and metadata package (`*_rights.json`, `*_metadata.json`, `*_thumb.jpg`).
- [ ] Upload: add YouTube Data API upload only after private/unlisted test uploads and policy review are reliable.

## Quality And Testing

- [x] Run syntax checks after every cleanup: `python -m compileall .`.
- [ ] Add a tiny sample-video smoke test for `pipelines/general_pipeline.py`.
- [x] Add unit tests for filename sequencing and download-history behavior in `sources/twitch_downloader.py`.
- [ ] Add tests for subtitle timing and max-duration trimming.
- [ ] Add tests for `core/history.py`, `core/thumbnail.py`, and `core/video_utils.py`.
- [x] Implement `core/dependency_check.py` — startup warnings for missing FFmpeg, ImageMagick, Demucs, models, fonts, music, and API keys.
- [x] Replace loose `print` statements with `logging` throughout all modules.

## Future Features

- [ ] Text animations — slide-in / typewriter / pop effects on headline text using per-frame MoviePy composition.
- [ ] YouTube upload helper with OAuth, private default visibility, retry/backoff, and metadata upload.
- [ ] Scheduled publishing only after manual approval.
- [ ] Analytics loop that records retention, watch time, likes, comments, and claim status.
- [ ] Safer source integrations for public-domain, Creative Commons, stock, or owned gameplay libraries.
- [ ] Creator-permission workflow for Twitch/Kick/YouTube clips.
- [ ] Twitch 2-step auth support in `sources/twitch_downloader.py` (cookie refresh or OAuth flow).
- [ ] Roboflow object detection integration in `pipelines/game_pipeline.py` — call Roboflow API instead of local YOLO for crop region.
- [ ] Admin panel in Flask (`web/routes/admin.py`) — user management, pipeline queue controls, system stats.
- [ ] Per-video YAML override file (`downloads/<game>-<id>_config.yaml`) merged on top of global config before each run.
- [ ] Auto-scraping improvements: scheduled clip discovery + channel watchlist in `sources/twitch_clip_finder.py`.

## Policy Reference (check before each publish — not actionable TODOs)

- Use only owned, licensed, public-domain, or clearly permissioned source video.
- Use only music and sounds cleared for commercial YouTube use.
- Add meaningful original commentary, parody, criticism, story, or analysis.
- Avoid non-original Shorts, reposted platform clips, and compilations with no original contribution.
- Disclose realistic altered/synthetic content in YouTube Studio when required.
- Keep titles, thumbnails, descriptions, and tags advertiser-friendly and accurate.
- Store proof of rights and transformation notes before publishing.
