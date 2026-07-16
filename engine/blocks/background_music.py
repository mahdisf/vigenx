"""Background-music / audio-mix block.

Lays a background track (random from a folder or a specific file) under the video
and optionally mixes in a narration audio track, reproducing the music-mixing stage
of the speaker/game pipelines (loop/subclip to length, volume ducking, composite).
"""
from __future__ import annotations

import logging
import os
import random

from engine.block import PREVIEW_FRAME, ParamSpec, PipelineBlock, PortSpec
from engine.clipkit import derive, load_clip, save_frame
from engine.context import ExecutionContext
from engine.ports import AUDIO, MEDIA, AudioRef
from engine.registry import register_block

log = logging.getLogger(__name__)
_AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".ogg")


@register_block
class BackgroundMusicBlock(PipelineBlock):
    type_id = "background_music"
    title = "Background Music"
    category = "audio"
    description = "Mix a background track (and optional narration) under the video."
    preview_kind = PREVIEW_FRAME  # audio-only change; show the input frame

    inputs = [
        PortSpec("media", MEDIA),
        PortSpec("narration", AUDIO, required=False),
    ]
    outputs = [PortSpec("media", MEDIA)]
    params = [
        ParamSpec("music_folder", "folder", "", label="Music folder",
                  help="Blank = config music_folder. A random track is picked from it."),
        ParamSpec("track", "file", "", label="Specific track",
                  help="Blank = random track from the folder."),
        ParamSpec("music_volume", "float", 0.15, min=0.0, max=1.0, label="Music volume"),
        ParamSpec("voice_volume", "float", 0.8, min=0.0, max=1.0, advanced=True,
                  label="Narration volume"),
    ]

    def _pick_track(self, ctx) -> str:
        track = self.p("track", "")
        if track and os.path.isfile(track):
            return track
        folder = self.p("music_folder", "") or getattr(ctx.config, "music_folder", "")
        if folder and os.path.isdir(folder):
            choices = [f for f in os.listdir(folder) if f.lower().endswith(_AUDIO_EXTS)]
            if choices:
                return os.path.join(folder, random.choice(choices))
        return ""

    def _apply(self, ctx, inputs):
        from moviepy.audio.fx import all as afx  # type: ignore[import]
        from moviepy.editor import AudioFileClip, CompositeAudioClip  # type: ignore[import]

        media = inputs["media"]
        clip = load_clip(media)
        layers = []
        if clip.audio is not None:
            layers.append(clip.audio)

        # narration first (kept near full volume)
        narration = inputs.get("narration")
        if isinstance(narration, AudioRef) and os.path.isfile(narration.path):
            voice = AudioFileClip(narration.path).fx(afx.volumex, self.p("voice_volume", 0.8))
            layers.append(voice)

        track = self._pick_track(ctx)
        if track:
            music = AudioFileClip(track)
            if music.duration > clip.duration:
                start_t = random.uniform(0, music.duration - clip.duration)
                music = music.subclip(start_t, start_t + clip.duration)
            elif music.duration < clip.duration:
                music = music.fx(afx.audio_loop, duration=clip.duration)
            music = music.fx(afx.volumex, self.p("music_volume", 0.15))
            layers.append(music)

        if not layers:
            return media
        clip = clip.set_audio(CompositeAudioClip(layers) if len(layers) > 1 else layers[0])
        return derive(media, clip)

    def process(self, ctx: ExecutionContext, inputs: dict) -> dict:
        return {"media": self._apply(ctx, inputs)}

    def preview(self, ctx: ExecutionContext, inputs: dict, t: float):
        clip = load_clip(inputs["media"])
        return save_frame(clip, t, ctx.temp_path("preview_music.jpg"), max_width=720)
