# ViGenX - Content Regenerator

ViGenX is a local AI-assisted video production studio for turning long-form
footage, livestream VODs, talks, gameplay, and downloaded clips into short-form
vertical videos. It combines a visual pipeline editor, reusable graph templates,
legacy one-command pipelines, live job progress, preview rendering, and a manual
review queue so generated videos can be inspected before publishing.

The project is built for repeatable short-video workflows:

- Ingest local files, folders, globs, remote URLs, playlists, and selected social sources.
- Transcribe speech with Whisper and use subtitles as editable timeline data.
- Detect high-value moments, trim silence, assemble highlights, and reframe to 9:16.
- Add subtitles, music, narration, branding, color filters, intro/outro clips, thumbnails, and metadata.
- Use AI blocks for title/description generation, structured extraction, and commentary.
- Run jobs from the Flask UI, monitor progress through Server-Sent Events, and approve or reject finished output.
- Keep rights manifests and metadata next to generated media for upload review.

This is not a blind auto-upload bot. The default product flow is: create or load a
pipeline, generate output, review the result, verify rights and quality, then
publish deliberately.

## Product Overview

ViGenX has two editing modes.

| Mode | Best For | Interface |
|------|----------|-----------|
| Visual graph editor | Building reusable production workflows from blocks | `/editor` web page |
| Legacy pipelines | Fast command-style generation for known workflows | Web job form or Python CLI |

The visual editor is the main product surface. It uses React Flow on the frontend
and a typed Python DAG engine on the backend. Each block declares input ports,
output ports, editable parameters, and preview behavior. The graph validator
rejects missing inputs, cycles, unknown blocks, and incompatible port types before
a run starts.

The legacy pipelines remain available for direct execution and for simpler jobs:

- `GeneralPipeline`: basic trimming, silence removal, transcription, subtitles, face blur, export.
- `SpeakerPipeline`: speech-focused shorts with key-moment scoring, subtitles, transitions, and music.
- `GameHighlightPipeline`: gameplay highlights with vertical format, YOLO-assisted focus, Demucs separation, Gemini commentary, and TTS narration.

## Key Capabilities

| Area | Capabilities |
|------|--------------|
| Source intake | Local files, local folders, file globs, video URLs, playlists, Twitch helpers, Instagram profile enumeration when `instaloader` is installed |
| Editing | Cut/trim, silence trim, key moments, assemble moments, face blur, vertical crop, color filter, intro/outro |
| Audio | Background music, vocal separation with Demucs, TTS narration |
| AI | Whisper transcription, Gemini/Groq/NVIDIA LLM text blocks, structured extraction with Pydantic validation |
| Output | MP4 export, multi-clip export, thumbnails, metadata JSON, rights manifest JSON |
| Web UI | Dashboard, graph editor, new job form, job detail with live progress, review queue, settings |
| Graph UX | Typed ports, drag/drop blocks, inspector-generated forms, validation, auto-layout, undo/redo, copy/paste, duplicate, draft preview, frame preview |
| Operations | Background job execution, batch graph runs over selected source references, optional local scheduling/publishing helpers |

## Project Structure

```text
Code/
|-- assets/                 # Product assets used by the UI
|-- config/                 # AppConfig dataclass and default_config.toml
|-- core/                   # Shared media, AI, metadata, TTS, downloader, manifest utilities
|-- docs/                   # Design notes and editor benchmark documents
|-- engine/                 # ViGenX typed graph engine and built-in blocks
|-- pipelines/              # Legacy general, speaker, and game pipeline implementations
|-- sources/                # Source resolvers and platform-specific discovery helpers
|-- templates/              # Built-in graph templates: general, speaker, game
|-- tests/                  # pytest coverage for config, engine, API, templates, outputs
|-- web/                    # Flask app, routes, templates, static CSS/JS, background worker
|-- run_web.py              # Web UI entry point
|-- requirements.txt
|-- requirements-dev.txt
|-- requirements-coqui-tts.txt
|-- TODO.md
`-- README.md
```

Runtime folders such as `downloads/`, `output/`, `renders/`, `jobs/`, `musics/`,
`fonts/`, `credentials/`, and generated media are intentionally gitignored.

## Main Modules

| Module | Purpose |
|--------|---------|
| `config/settings.py` | `AppConfig`, TOML/YAML loading, LLM key store integration |
| `core/downloader.py` | `yt-dlp` video downloader with fallback behavior |
| `core/transcription.py` | Whisper transcription into subtitle segments |
| `core/gemini_client.py` | Gemini text and structured JSON generation |
| `core/llm.py` | Provider-agnostic LLM wrapper for Gemini, Groq, and NVIDIA NIM |
| `core/tts.py` | TTS abstraction using `pyttsx3` by default and Coqui in a separate env |
| `core/vocal_separator.py` | Demucs vocal/instrumental separation |
| `core/face_blur.py` | MediaPipe/OpenCV face blur processing |
| `core/manifest.py` | Rights manifest model and writer |
| `core/metadata.py` | Video metadata model and writer |
| `core/dependency_check.py` | Startup warnings for missing FFmpeg, API keys, models, and tools |
| `engine/graph.py` | Serializable and validated pipeline DAG |
| `engine/block.py` | Block, parameter, port, and preview abstractions |
| `engine/executor.py` | Full graph execution, per-node progress, frame preview, draft rendering |
| `engine/registry.py` | Built-in block registration and schema generation |
| `engine/templates.py` | Template load/save/list/delete helpers |
| `web/routes/api.py` | JSON API for editor blocks, templates, previews, source resolution, runs, schedule |
| `web/worker.py` | Background job runner for graph and legacy pipeline jobs |
| `sources/resolver.py` | Converts files, folders, globs, URLs, playlists, and Instagram sources into selectable media refs |

## Built-In Graph Templates

Templates are stored as JSON in `templates/` and can be loaded in the web editor.

| Template | Purpose |
|----------|---------|
| `general` | Source -> trim -> silence trim -> Whisper -> subtitles -> MP4 export |
| `speaker` | Source -> Whisper -> key moments -> moment assembly -> subtitles -> music -> export |
| `game` | Source -> trim -> vertical format -> color -> logo -> music -> export -> thumbnail |

You can save edited templates from the editor. Saved templates are regular graph
JSON documents with nodes, edges, parameters, positions, and metadata.

## Built-In Blocks

| Category | Blocks |
|----------|--------|
| Source | Source |
| Edit | Cut / Trim, Trim Silence, Assemble Moments, Face Blur, Subtitles |
| Effects | Vertical Format, Color Filter |
| Audio | Background Music, Narration (TTS), Vocal Separation |
| Branding | Logo Overlay, Intro / Outro |
| AI | Transcribe (Whisper), Key Moments, AI Text, AI Part Extraction |
| Output | Export MP4, Export Clips, Thumbnail |

The editor builds its palette and inspector from the block schemas exposed by
`GET /api/blocks`, so backend block definitions are the single source of truth.

## Requirements

Recommended environment:

- Python 3.10+.
- FFmpeg installed and available on `PATH`.
- A machine with enough disk space for downloaded media, renders, model caches, and temporary files.
- NVIDIA GPU and `h264_nvenc` only if you enable GPU encoding.

Core Python dependencies are listed in `requirements.txt`. Development-only
dependencies are in `requirements-dev.txt`.

Optional tools and packages:

| Tool | Used For |
|------|----------|
| ImageMagick | MoviePy text rendering on some systems |
| Demucs | Vocal/instrumental separation |
| Ultralytics YOLOv8 | Gameplay/object-aware processing; `yolov8n.pt` may be auto-downloaded |
| `instaloader` | Instagram profile enumeration |
| `openai` | Groq and NVIDIA OpenAI-compatible LLM providers |
| `google-api-python-client` and `google-auth-oauthlib` | YouTube upload helper if using local publisher modules |
| `instagrapi` | Instagram Reels upload helper if using local publisher modules |
| Playwright | Browser-driven publisher fallback for platforms such as TikTok |

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install runtime dependencies:

```powershell
pip install -r requirements.txt
```

Install test/development dependencies:

```powershell
pip install -r requirements-dev.txt
```

Confirm FFmpeg is available:

```powershell
ffmpeg -version
```

If MoviePy text rendering needs ImageMagick, install ImageMagick and set
`imagemagick_binary` in `config/default_config.toml`.

Do not install Coqui `TTS` into the main project environment. It can conflict
with MediaPipe through protobuf dependencies. If Coqui voices are required,
create a separate environment and install:

```powershell
pip install -r requirements-coqui-tts.txt
```

## API Keys And Secrets

Secrets can be provided through environment variables or through the Settings
page, which writes selected provider keys into the gitignored `credentials/`
folder. Environment variables take precedence.

```powershell
setx GOOGLE_API_KEY "YOUR_GEMINI_KEY"
setx GROQ_API_KEY "YOUR_GROQ_KEY"
setx NVIDIA_API_KEY "YOUR_NVIDIA_KEY"
setx TWITCH_CLIENT_ID "YOUR_TWITCH_CLIENT_ID"
setx TWITCH_CLIENT_SECRET "YOUR_TWITCH_SECRET"
```

Restart the terminal after using `setx`.

Do not commit `.env`, OAuth tokens, browser cookies, platform sessions, or
anything under `credentials/`.

## Configuration

Default values live in `config/settings.py`; project overrides live in
`config/default_config.toml`.

Example:

```toml
app_name = "ViGenX"
game_name = "Counter-Strike"
whisper_model = "small"
max_duration = 59
use_gpu_encoder = false
video_codec = "libx264"
audio_codec = "aac"
crf = 18
preset = "medium"
tts_engine = "pyttsx3"
llm_provider = "gemini"
gemini_text_model = "gemini-2.5-flash"
imagemagick_binary = 'C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe'
```

Editable runtime settings are also available at `/settings`. API keys are shown
there as configured/not configured without exposing secret values.

## Running The Web App

```powershell
python run_web.py
```

Open:

```text
http://127.0.0.1:5000
```

Main pages:

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | `/` | View all jobs and current status |
| Pipeline Editor | `/editor` | Build, preview, validate, save, and run block graphs |
| New Job | `/jobs/new` | Submit a legacy pipeline job |
| Job Detail | `/jobs/<job_id>` | Watch live progress, logs, node status, output path |
| Review Queue | `/review` | Approve or reject generated videos |
| Settings | `/settings` | Edit selected config fields and manage LLM key status |

The scheduler is created by the Flask app and started by `run_web.py` outside the
debug reloader parent process.

## Visual Editor Workflow

1. Open `/editor`.
2. Load a built-in template or add blocks from the palette.
3. Connect typed ports. Invalid port combinations are blocked by validation.
4. Select a node to edit parameters in the inspector.
5. Use a Source block with a local file path or a URL.
6. Resolve sources to select one or more media references for batch runs.
7. Use frame preview or draft clip preview to inspect intermediate output.
8. Click Validate before running.
9. Click Run to create a background graph job.
10. Review finished output in the review queue.

Useful editor shortcuts:

| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+C` | Copy selected node |
| `Ctrl+V` | Paste |
| `Ctrl+D` | Duplicate |
| `Delete` or `Backspace` | Remove selected node or edge |
| Double-click canvas | Quick-add a compatible node |

## Source Inputs

The source resolver accepts:

- A single local video file.
- A local folder containing video files.
- A glob such as `D:\clips\*.mp4`.
- A direct video URL supported by `yt-dlp`.
- A playlist/channel/page URL that `yt-dlp` can enumerate.
- An Instagram URL, `@handle`, or username when `instaloader` is installed.

Resolved sources become selectable media references. In a batch graph run, each
selected reference overrides the Source block parameters for one execution.

## Legacy CLI Usage

The original pipelines can still be run directly.

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

## Generated Output

Pipeline outputs are written to configured output folders such as `output/`,
`speaker-output/`, and `renders/`.

Common generated files:

| File | Contents |
|------|----------|
| `*.mp4` | Rendered video output |
| `*_rights.json` or `video_rights.json` | Source URL, permission status, music license, AI tools used, policy checklist |
| `*_metadata.json` or `video_metadata.json` | Title, description, tags, render settings, timestamps |
| `*_details.txt` or `video_details.txt` | Human-readable title and description for selected workflows |
| `*.png` | Thumbnail or extracted preview image |
| `jobs/*.json` | Job status, progress, output paths, node status, and logs |
| `jobs/schedule.json` | Optional scheduled publish items |

Rights manifest checklist values default conservatively and must be reviewed
manually before upload.

## Optional Publishing And Scheduling

The API includes endpoints for uploader status and scheduled publishing:

- `GET /api/uploaders`
- `GET /api/schedule`
- `POST /api/schedule`
- `DELETE /api/schedule/<item_id>`
- `POST /api/schedule/run_due`

Local publisher helpers may include folder publishing, YouTube Data API upload,
Instagram Reels upload, and Playwright-driven browser publishing. These depend
on optional packages and credentials. Treat publishing as a separate configured
deployment concern, not as part of the default development setup.

Recommended production behavior:

- Keep generated jobs in `awaiting_review` until a human approves them.
- Publish as `private` or `unlisted` first when a platform supports it.
- Store OAuth tokens and sessions only in `credentials/`.
- Keep a rights manifest and metadata file for every published asset.

## Tests

Run all tests:

```powershell
pytest tests/ -v
```

Current test areas include:

- Config loading.
- Filename sequencing and download history.
- Rights manifest and metadata generation.
- Gemini structured output behavior.
- Graph validation, registry, templates, executor, AI blocks, resolver routing.
- Flask API behavior.
- Output and template integrity.

## Runtime Folders

These folders are created or used locally and are gitignored:

| Folder | Purpose |
|--------|---------|
| `downloads/` | Downloaded input videos |
| `speaker-downloads/` | Speaker pipeline source downloads |
| `clips/` | Twitch clips and short source clips |
| `output/` | Generated output videos, metadata, history, local publisher helpers |
| `speaker-output/` | Speaker pipeline output |
| `renders/` | Graph/editor render tree |
| `jobs/` | Job JSON files and schedule store |
| `musics/` | Background tracks; use only commercially licensed audio |
| `fonts/` | Fonts for subtitles and overlays |
| `voice_samples/` | Optional voice cloning/reference samples |
| `TTS/` | Optional Coqui assets or cache |
| `credentials/` | OAuth tokens, API key store, cookies, platform sessions |

## Current Boundaries

- Full graph runs are supported; draft-from-node preview is supported. A fully
  materialized "run from this node only" path is still a future enhancement.
- Preview caching is in memory for editor responsiveness. Persistent intermediate
  caching across separate full runs is not yet generalized.
- Some publisher modules and platform sessions are local/runtime concerns and
  depend on optional packages not installed by default.
- Platform APIs and monetization policies can change. Re-check platform rules
  before relying on automated publishing or monetization assumptions.

## Content Rights And Monetization

ViGenX can transform media, but automation does not guarantee copyright safety,
fair use, or monetization eligibility.

Practical policy:

- Prefer original footage, your own gameplay, licensed stock, public domain media, or Creative Commons media with commercial rights.
- Get commercial rights for video, music, voices, images, fonts, logos, and any third-party assets.
- Treat random Twitch, YouTube, Kick, Instagram, and TikTok clips as high risk unless you have permission or a strong commentary, criticism, parody, or transformative reason.
- Adding subtitles, music, cropping, or simple trimming is usually not enough by itself to make reused content safe.
- Review the rights manifest before every upload.
- Disclose realistic altered or synthetic content when a platform requires it.

Policy references:

- [Fair use on YouTube](https://support.google.com/youtube/answer/9783148)
- [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392)
- [YouTube Shorts monetization policies](https://support.google.com/youtube/answer/12504220)
- [YouTube Partner Program overview](https://support.google.com/youtube/answer/72851)
- [How Content ID works](https://support.google.com/youtube/answer/2797370)
- [Disclosing altered or synthetic content](https://support.google.com/youtube/answer/14328491)
- [Upload a video with the YouTube Data API](https://developers.google.com/youtube/v3/guides/uploading_a_video)

## Short-Video Workflow Ideas

Best-fit workflows for this codebase:

1. Gaming highlights from original or licensed gameplay.
2. Speaker clips from podcasts, talks, classes, or interviews where you have rights.
3. Tutorial recaps with generated subtitles, branded overlays, and thumbnails.
4. Product or tool walkthroughs using original screen recordings.
5. AI-assisted narration over licensed stock or original footage.
6. Clip compilations only when source permissions and monetization rules are clear.
