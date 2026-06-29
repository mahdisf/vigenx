# Content Regenerator

Python toolkit for turning long-form videos into short-form content. The pipeline downloads source video, transcribes speech, detects key moments, trims and edits, adds subtitles/music/commentary, and exports a vertical-format short ready for human review before any upload.

A Flask web UI lets you submit jobs, watch live progress via Server-Sent Events, and approve or reject videos in a review queue before publishing.

## Project Shape

```
Code/
├── config/              # AppConfig dataclass + default_config.toml
├── core/                # Shared utilities (downloader, transcription, face_blur, TTS, Gemini, manifest, metadata …)
├── pipelines/           # BasePipeline + general / speaker / game pipeline implementations
├── sources/             # Twitch VOD downloader and clip finder
├── web/                 # Flask app (routes, templates, static assets, job store, background worker)
├── tests/               # pytest unit tests
├── run_web.py           # Web UI entry point
├── requirements.txt
├── requirements-coqui-tts.txt
├── requirements-dev.txt
└── TODO.md
```

| Module | Purpose |
|--------|---------|
| `config/settings.py` | `AppConfig` dataclass; all pipeline constants live here |
| `config/default_config.toml` | TOML overrides loaded on top of defaults |
| `core/gemini_client.py` | Gemini text generation + `generate_structured()` with Pydantic validation |
| `core/tts.py` | TTS wrapper (pyttsx3 default; Coqui in separate env) |
| `core/vocal_separator.py` | Demucs vocal/instrumental separation |
| `core/transcription.py` | Whisper transcription → `SubtitleSegment` list |
| `core/downloader.py` | yt-dlp video downloader with cookie fallback |
| `core/face_blur.py` | MediaPipe + OpenCV face blur frame processor |
| `core/audio_utils.py` | ffprobe duration, ffmpeg audio extraction, silence detection |
| `core/manifest.py` | `RightsManifest` dataclass + `save_manifest()` |
| `core/metadata.py` | `VideoMetadata` dataclass + `save_metadata()` |
| `core/dependency_check.py` | Startup warnings for missing FFmpeg, models, API keys |
| `pipelines/general_pipeline.py` | General editor: download, Whisper subtitles, silence trim, face blur, export |
| `pipelines/speaker_pipeline.py` | Speaker shorts: key-moment scoring, transitions, subtitles, music |
| `pipelines/game_pipeline.py` | Game highlights: YOLO crop, Demucs, Gemini commentary, TTS, vertical format |
| `sources/twitch_downloader.py` | Twitch VOD/playlist download with sequential naming and history dedup |
| `sources/twitch_clip_finder.py` | Twitch API clip discovery by game, view count, and date |
| `web/` | Flask web UI — dashboard, new job form, live progress, review queue, settings |

## Setup

Create a virtual environment and install dependencies:

```powershell
pip install -r requirements.txt
```

For development tools (pytest, pydantic):

```powershell
pip install -r requirements-dev.txt
```

**Do not** install Coqui `TTS` into the main environment — it conflicts with `mediapipe` via protobuf. If you need Coqui voices, create a separate environment:

```powershell
pip install -r requirements-coqui-tts.txt
```

Install FFmpeg and confirm it is on PATH:

```powershell
ffmpeg -version
```

Optional system tools:
- **ImageMagick** — for MoviePy text rendering (update `imagemagick_binary` in `config/default_config.toml`)
- **Demucs** — `pip install demucs` — for vocal separation
- **YOLOv8** model (`yolov8n.pt`) — auto-downloaded by Ultralytics on first run

## Environment Variables

```powershell
setx GOOGLE_API_KEY  "YOUR_GEMINI_KEY"
setx TWITCH_CLIENT_ID     "YOUR_TWITCH_CLIENT_ID"
setx TWITCH_CLIENT_SECRET "YOUR_TWITCH_SECRET"
```

Reopen the terminal after setting environment variables. API keys are **never** stored in config files.

## Configuration

Edit `config/default_config.toml` to override any `AppConfig` field:

```toml
game_name = "Valorant"
whisper_model = "medium"
use_gpu_encoder = true     # requires NVIDIA GPU + h264_nvenc driver
tts_engine = "pyttsx3"     # or "coqui" in a separate env
max_duration = 59
imagemagick_binary = 'C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe'
```

All editable fields are also available via the web Settings page.

## Running the Web UI

```powershell
python run_web.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

- **Dashboard** — all jobs with status and progress
- **New Job** — pick pipeline type, source (local file or URL), and options
- **Job Detail** — live progress via SSE, scrollable log
- **Review Queue** — approve or reject completed videos before any upload
- **Settings** — edit pipeline defaults; API key status shown (keys set via env vars only)

## CLI Usage

Each pipeline is also runnable from the command line:

```powershell
# General editor
python -m pipelines.general_pipeline --input .\video.mp4 --out .\out.mp4 --whisper --trim-silence

# Speaker short
python -m pipelines.speaker_pipeline --input .\talk.mp4 --whisper-model small

# Game highlight
python -m pipelines.game_pipeline --game-name "Counter-Strike" --auto
python -m pipelines.game_pipeline --game-name "Counter-Strike" --no-auto --video-id 3 --video-title "ace clip"
python -m pipelines.game_pipeline --game-name "Counter-Strike" --url "https://www.twitch.tv/..."

# Twitch VOD downloader
python -m sources.twitch_downloader "https://www.twitch.tv/videos/VIDEO_ID" "Counter-Strike"

# Twitch clip finder
python -m sources.twitch_clip_finder
```

## Output Files

Every pipeline run produces three files next to the output MP4:

| File | Contents |
|------|---------|
| `video_rights.json` | Rights manifest: source URL, permission status, music license, AI tools used, policy checklist |
| `video_metadata.json` | Title, description, tags, render settings, timestamps |
| `video_details.txt` | Human-readable title and description (game pipeline only) |

The policy checklist in the manifest defaults to all `false` and must be filled in manually before uploading.

## Running Tests

```powershell
pytest tests/ -v
```

Tests cover config loading, filename sequencing, download history dedup, rights manifest, metadata, and Gemini structured output.

## Project Folders (runtime, gitignored)

- `downloads/`, `speaker-downloads/`, `clips/` — source videos
- `output/`, `speaker-output/` — generated videos and metadata
- `jobs/` — Flask job state JSON files
- `musics/` — background tracks (use only commercially licensed audio)
- `fonts/` — fonts for subtitles and overlays
- `voice_samples/`, `TTS/` — TTS assets

## Copyright and Monetization

Checked against official YouTube/Google sources on 2026-06-09. This is engineering guidance, not legal advice.

- Transformative editing helps, but fair use is case-by-case. Commentary, criticism, parody, and new meaning are stronger than simply trimming, adding subtitles, or adding music.
- YouTube monetization has a separate reused-content policy. A channel can lose monetization even when a video has no copyright strike if the channel mainly repackages other people's content.
- Shorts monetization excludes non-original Shorts such as unedited clips or compilations with no original content added.
- You need commercial rights for the video, music, voice, images, fonts, and other assets.
- Realistic altered or synthetic content must be disclosed in YouTube Studio when it meaningfully changes reality.

Safer source strategy:
- Prefer original footage, your own gameplay, paid/licensed stock, public domain footage, or Creative Commons content with commercial rights.
- Store source URL, license, creator permission, music license, and transformation notes (`*_rights.json`) for every generated video.
- Treat random Twitch/YouTube/Kick clips as high risk unless you have permission or a strong commentary/parody reason.

## Short-Video Idea Backlog

Ranked from best current fit to weaker/riskier automation:

1. Automated gaming highlights — Roblox, Fortnite, Minecraft, Valorant, Counter-Strike, GTA.
2. Funny food hacks or recipe mashups using public/owned data and stock/original visuals.
3. AI-generated meme compilations using original templates and trend prompts.
4. Fictional "day in the life" AI simulations.
5. Tech gadget tips with humorous commentary.
6. VTuber-style motivational quotes with comedic twists.
7. Behind-the-scenes AI business skits.
8. Natural-disaster or "what if" simulations, with sensitivity checks.
9. Try-on haul parodies using licensed/product API assets.
10. Historical fact recreations with humor.

## Policy Sources

- [Fair use on YouTube](https://support.google.com/youtube/answer/9783148)
- [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392)
- [YouTube Shorts monetization policies](https://support.google.com/youtube/answer/12504220)
- [YouTube Partner Program overview](https://support.google.com/youtube/answer/72851)
- [How Content ID works](https://support.google.com/youtube/answer/2797370)
- [Disclosing altered or synthetic content](https://support.google.com/youtube/answer/14328491)
- [Upload a video with the YouTube Data API](https://developers.google.com/youtube/v3/guides/uploading_a_video)
