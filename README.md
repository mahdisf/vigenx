# Content Generator — AI Video Tools

This repository contains Python scripts to generate/edit short-form videos using:
- **YouTube/Twitch downloading** (`yt-dlp` / Twitch API)
- **Whisper transcription**
- **Silence trimming**
- **Scene detection**
- **Face blurring**
- **Optional audio separation (Demucs)**
- **Gemini text generation** (optional)

> **Main entrypoints**
> - `ai_video_editor.py` – general “download → process → export” editor
> - `speaker-short-maker.py` – generate a short video from a spoken clip (URL or local file)

## Prerequisites

### 1) FFmpeg
Both scripts rely on `ffmpeg` for audio/video handling.

Make sure `ffmpeg` is available in your PATH:

```bash
ffmpeg -version
```

### 2) Demucs (optional, for vocal separation)
`speaker-short-maker.py` uses `demucs` via `voice_remover.py`.

```bash
pip install demucs
```

Also ensure the `demucs` CLI is reachable:

```bash
demucs --help
```

### 3) ImageMagick (optional)
`speaker-short-maker.py` attempts to configure ImageMagick for MoviePy text rendering.
If ImageMagick isn’t installed, text overlays may degrade.

## Setup

### 1) Create a virtual environment (recommended)

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

## Environment variables (optional)

### Google Gemini
If you use `gemini_text.py` or parts of scripts that call Gemini:

- `GOOGLE_API_KEY`

Example (Windows PowerShell):

```powershell
setx GOOGLE_API_KEY "YOUR_KEY_HERE"
```

Reopen your terminal after setting environment variables.

### Twitch (only if you use Twitch scripts)
- `TWITCH_CLIENT_ID`
- `TWITCH_CLIENT_SECRET`

## How to run

### A) General editor: `ai_video_editor.py`

Usage:

```bash
python ai_video_editor.py --input <path_to_video>
```

Or download from URL:

```bash
python ai_video_editor.py --url <video_url>
```

Common options:
- `--out output.mp4`
- `--whisper` (burn subtitles)
- `--trim-silence`
- `--scene-detect`
- `--blur-faces`

Example: local input + subtitles + face blur:

```bash
python ai_video_editor.py --input .\input.mp4 --out .\output.mp4 --whisper --blur-faces
```

### B) Speaker short maker: `speaker-short-maker.py`

Create from a local file:

```bash
python speaker-short-maker.py --input .\speaker.mp4 --output short.mp4
```

Create from URL:

```bash
python speaker-short-maker.py --url <video_url> --output short.mp4
```

Common options:
- `--blur-faces`
- `--language <code>` (e.g., `en`)
- `--whisper-model <tiny|base|small|medium|large>`
- `--no-music`

Example:

```bash
python speaker-short-maker.py --input .\speaker.mp4 --blur-faces --whisper-model small --output short.mp4
```

## Project structure

After setup, ensure the following folders (used by scripts):
- `./musics` – background music
- `./fonts` – fonts (Roboto_Condensed-Black.ttf)
- `speaker-output/` – generated shorts
- `speaker-downloads/` – downloaded videos (when using URL mode)

## Troubleshooting

### 1) “ffprobe not found” / “ffmpeg not found”
Install/enable FFmpeg and ensure it’s in PATH.

### 2) Subtitle rendering issues
- Install ImageMagick (optional)
- Ensure fonts exist in `./fonts`

### 3) Demucs errors
- Ensure `demucs` is installed
- Ensure `demucs` model downloads succeed

## Notes on cleanup
This repository was cleaned to remove duplicate/experimental scripts and invalid filenames. The remaining scripts represent the stable pipeline entrypoints.

