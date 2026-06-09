# Video Regenerator

Python tools for turning long, unpolished source videos into short-form, more transformative videos. The intended pipeline is:

1. Find or download a permitted source video.
2. Detect useful moments with transcript, audio, scene, or game/context signals.
3. Trim the strongest sections into a short edit.
4. Add subtitles, background music, commentary/voiceover, vertical framing, and privacy edits.
5. Review rights, policy risk, and output quality before any YouTube upload.

This repo is a prototype toolkit, not a finished fully automated YouTube channel system. The code currently covers download, transcription, trimming, face blur, music, voiceover/commentary helpers, Twitch discovery, and game-highlight editing. Automated upload is still a future milestone because copyright, monetization, and spam/inauthentic-content risk need a human review gate.

## Current Project Shape

| File | Purpose |
| --- | --- |
| `ai_video_editor.py` | General editor for local files or URLs. Supports yt-dlp download, Whisper subtitles, silence trimming, scene detection, face blur, and MP4 export. |
| `speaker_short_maker.py` | Creates under-60-second speaker clips from a local file or URL using Whisper, simple key-moment scoring, transitions, subtitles, and optional background music. |
| `game_highlight_short_maker.py` | Counter-Strike/Twitch highlight prototype. Adds vertical crop, background music, Gemini-generated commentary hooks, TTS voiceover, stylized overlays, and optional Demucs vocal separation. |
| `twitch_video_downloader.py` | Downloads Twitch VODs/playlists with sequential naming and a download history file. |
| `twitch_clip_finder.py` | Uses the Twitch API to find recent clips for a game and download candidates. |
| `gemini_client.py` | Thin Gemini helper for text generation and video moment commentary prompts. |
| `text_to_speech.py` | Voiceover helper. Uses `pyttsx3` by default and can use Coqui TTS only when installed separately. |
| `vocal_separator.py` | Demucs helper that separates vocals and instrumental audio. |
| `requirements.txt` | Main dependency list for the remaining source files. |
| `requirements-coqui-tts.txt` | Optional Coqui TTS dependency file for a separate voice environment. |
| `TODO.md` | Roadmap and cleanup/workflow checklist. |

Removed files were scratch tests, duplicate requirement files, old duplicate script versions, redundant intro/report source notes, or generated/archive artifacts.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Do not install Coqui `TTS` into the main environment. It can conflict with `mediapipe` through incompatible `protobuf` requirements. The default project voiceover path uses `pyttsx3`. If you specifically want Coqui voices, create a separate environment and install:

```powershell
pip install -r requirements-coqui-tts.txt
```

Install FFmpeg and confirm it is available:

```powershell
ffmpeg -version
```

Optional system tools:

- ImageMagick, for some MoviePy text rendering paths.
- Demucs CLI, installed through `pip install demucs`, for vocal separation.
- Coqui TTS in a separate environment, only if you need higher-quality local voice generation than `pyttsx3`.
- A local `yolov8n.pt` model or Ultralytics download access for the game-highlight prototype.

## Environment Variables

Some helpers need API credentials:

```powershell
setx GOOGLE_API_KEY "YOUR_KEY_HERE"
setx TWITCH_CLIENT_ID "YOUR_CLIENT_ID"
setx TWITCH_CLIENT_SECRET "YOUR_CLIENT_SECRET"
```

Reopen the terminal after setting environment variables.

## Usage

General editor from a local file:

```powershell
python ai_video_editor.py --input .\input.mp4 --out .\output.mp4 --whisper --trim-silence --blur-faces
```

General editor from a URL:

```powershell
python ai_video_editor.py --url "https://youtu.be/VIDEO_ID" --out .\output.mp4 --whisper
```

Speaker short maker:

```powershell
python speaker_short_maker.py --input .\speaker.mp4 --output short.mp4 --whisper-model small
```

Twitch VOD downloader:

```powershell
python twitch_video_downloader.py "https://www.twitch.tv/videos/VIDEO_ID"
```

Twitch clip finder:

```powershell
python twitch_clip_finder.py
```

Game highlight prototype:

```powershell
python game_highlight_short_maker.py
```

Note: `game_highlight_short_maker.py` still has configuration at the top of the file (`GAME_NAME`, `INPUT_DIR`, `OUTPUT_DIR`, `selected_videos.txt`). Refactoring it into a real CLI is a high-priority TODO item.

## Project Folders

These folders are local/runtime folders and are ignored by git:

- `downloads/`, `clips/`, `speaker-downloads/` - downloaded source videos.
- `output/`, `speaker-output/` - generated videos and metadata.
- `musics/` - local background tracks. Store only tracks you are allowed to use commercially.
- `fonts/` - local fonts for subtitle and overlay rendering.
- `voice_samples/`, `TTS/` - local voice/TTS assets.

## Copyright And Monetization Reality

Checked against official YouTube/Google sources on 2026-06-08. This is engineering guidance, not legal advice.

- Transformative editing helps, but fair use is case-by-case. Commentary, criticism, parody, and new meaning are stronger than simply trimming, adding subtitles, or adding music.
- YouTube monetization has a separate reused-content policy. A channel can lose monetization even when a video has no copyright strike if the channel mainly repackages other people's content without significant original commentary, substantive edits, or clear entertainment/educational value.
- Shorts monetization excludes non-original Shorts such as unedited clips, reuploads from other platforms, and compilations with no original content added.
- You need commercial rights for the video, music, voice, images, fonts, and other assets. Unlicensed music or visual material can trigger Content ID, blocking, revenue redirection, or takedown risk.
- Content ID claims and copyright strikes are different. Content ID can block, track, or monetize for the rights holder. A valid copyright removal request can remove the video and apply a strike.
- YPP ad revenue eligibility generally requires either 1,000 subscribers plus 4,000 valid public watch hours in the last 12 months, or 1,000 subscribers plus 10 million valid public Shorts views in the last 90 days. Expanded YPP fan-funding access has lower thresholds in eligible regions.
- Realistic altered or synthetic content must be disclosed in YouTube Studio when it meaningfully changes reality, such as cloning someone else's voice or making a real person appear to say or do something they did not.
- Upload automation should use the YouTube Data API with OAuth. Unverified API projects may be restricted to private uploads until audited. A human review step is recommended before public release.

Safer source strategy:

- Prefer original footage, your own gameplay, paid/licensed stock, public domain footage, or Creative Commons content with commercial rights.
- Store source URL, license, creator permission, music license, and transformation notes for every generated video.
- Treat random Twitch/YouTube/Kick clips as high risk unless you have permission or a very strong commentary/parody reason.

## Feasibility Summary

The technical side is feasible: Python, FFmpeg/MoviePy, Whisper, yt-dlp, Gemini/OpenAI-style models, TTS/voiceover tooling, Demucs, and the YouTube Data API can automate most of the workflow.

The business/legal side is the constraint. A fully automated channel that mass-produces reused clips is risky for monetization and copyright. The best direction is a semi-automated review pipeline that makes clearly original edits, keeps proof of rights, and starts with safer niches.

Best first niche for this repo: gaming highlights, especially clips where you own the gameplay or have creator permission. The existing code already points in that direction.

## Short-Video Idea Backlog

Ranked from best current fit to weaker/riskier automation:

1. Automated gaming highlights, such as Roblox, Fortnite, Minecraft, Valorant, Counter-Strike, or GTA clips.
2. Funny food hacks or recipe mashups using public/owned data and stock/original visuals.
3. AI-generated meme compilations using original templates and trend prompts.
4. Fictional "day in the life" AI simulations.
5. Tech gadget tips with humorous commentary.
6. VTuber-style motivational quotes with comedic twists.
7. Behind-the-scenes AI business skits.
8. Natural-disaster or "what if" simulations, with sensitivity checks.
9. Try-on haul parodies using licensed/product API assets.
10. Historical fact recreations with humor.
11. Fitness fail animations or pose-analysis explainers.
12. Lofi study tips with licensed royalty-free music.
13. Celebrity news satire, with strict accuracy and defamation checks.
14. DIY home hacks gone wrong using original/stock assets.
15. Travel destination budget-vs-luxury comparisons.
16. Public-domain movie recap parodies.
17. Sports highlight memes based on licensed footage or data-only visuals.
18. Science fact explainers with jokes.
19. Virtual ASMR item unboxings.
20. Weather update roasts.

## Policy Sources

- [Fair use on YouTube](https://support.google.com/youtube/answer/9783148)
- [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392)
- [YouTube Shorts monetization policies](https://support.google.com/youtube/answer/12504220)
- [What kind of content can I monetize?](https://support.google.com/youtube/answer/2490020)
- [YouTube Partner Program overview and eligibility](https://support.google.com/youtube/answer/72851)
- [How Content ID works](https://support.google.com/youtube/answer/2797370)
- [Understand copyright strikes](https://support.google.com/youtube/answer/2814000)
- [Disclosing altered or synthetic content](https://support.google.com/youtube/answer/14328491)
- [Upload a video with the YouTube Data API](https://developers.google.com/youtube/v3/guides/uploading_a_video)
- [Videos: insert API reference](https://developers.google.com/youtube/v3/docs/videos/insert)
