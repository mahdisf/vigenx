# TODO

## Completed Cleanup

- [x] Inspect the repository scripts, docs, and generated artifacts.
- [x] Read and merge `intro.md`, `grok_idea_report.pdf`, and the old README/TODO direction.
- [x] Verify current YouTube copyright, monetization, Shorts, AI disclosure, and upload rules from official sources.
- [x] Remove scratch scripts, duplicate requirements, old duplicate script versions, redundant intro/report files, and local archive/PDF artifacts.
- [x] Rename remaining scripts to clearer importable Python names.
- [x] Consolidate dependencies into `requirements.txt`.
- [x] Split optional Coqui TTS out of the main requirements to avoid the `mediapipe`/`protobuf` conflict.
- [x] Remove the Gemini API call that ran during module import.

## Immediate Code Work

- [ ] Refactor `game_highlight_short_maker.py` into a real CLI with arguments for game name, source video, output path, URL, music folder, and selected-video mode.
- [ ] Move shared settings into a small config object or config file instead of top-of-file constants.
- [ ] Add a rights manifest JSON for every generated video: source URL, source owner, permission/license, music license, AI tools used, and transformation notes.
- [ ] Replace the simple speaker key-moment heuristic with a scoring layer that considers transcript, laughter/emotion, scene changes, audio spikes, comments/chat, and user-configured duration.
- [ ] Make Gemini/OpenAI commentary generation return strict JSON and validate it before editing.
- [ ] Add a human review queue before any upload step.
- [ ] Add structured output metadata next to every video: title, description, tags, timestamps, source info, policy checklist, and render settings.

## MVP Pipeline

- [ ] Input: accept local file, YouTube URL, Twitch VOD/clip URL, or a vetted source list.
- [ ] Rights gate: reject sources without clear permission, public-domain status, or commercial license.
- [ ] Download: save source video and source metadata.
- [ ] Analyze: transcribe with Whisper, detect scenes/silence, and score highlight candidates.
- [ ] Edit: trim selected moments, convert to vertical format, add subtitles, commentary/TTS, music, and optional face blur.
- [ ] Review: show preview plus rights/monetization checklist.
- [ ] Export: write final MP4 and metadata package.
- [ ] Upload: add YouTube Data API upload only after private/unlisted test uploads and policy review are reliable.

## Policy Checklist

- [ ] Use only owned, licensed, public-domain, or clearly permissioned source video.
- [ ] Use only music and sounds cleared for commercial YouTube use.
- [ ] Add meaningful original commentary, parody, criticism, story, or analysis. Do not rely on subtitles/music alone as transformation.
- [ ] Avoid non-original Shorts, reposted platform clips, and compilations with no original contribution.
- [ ] Disclose realistic altered/synthetic content in YouTube Studio when required.
- [ ] Keep titles, thumbnails, descriptions, and tags advertiser-friendly and accurate.
- [ ] Store proof of rights and transformation notes before publishing.

## Quality And Testing

- [ ] Run syntax checks after every cleanup: `python -m compileall .`.
- [ ] Add a tiny sample-video smoke test for `ai_video_editor.py`.
- [ ] Add unit tests for filename sequencing and download-history behavior in `twitch_video_downloader.py`.
- [ ] Add tests for subtitle timing and max-duration trimming.
- [ ] Add error handling for missing FFmpeg, ImageMagick, Demucs, models, fonts, music, and API keys.
- [ ] Add logging instead of loose `print` statements.

## Future Features

- [ ] YouTube upload helper with OAuth, private default visibility, retry/backoff, and metadata upload.
- [ ] Scheduled publishing only after manual approval.
- [ ] Analytics loop that records retention, watch time, likes, comments, and claim status.
- [ ] Safer source integrations for public-domain, Creative Commons, stock, or owned gameplay libraries.
- [ ] Creator-permission workflow for Twitch/Kick/YouTube clips.
