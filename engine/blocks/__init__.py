"""Built-in block library.

Importing this package registers every available block. Each block module is
imported defensively: blocks that depend on optional heavy libraries (whisper,
moviepy, mediapipe, demucs, ultralytics, ...) are skipped with a debug log if their
dependency is missing, so the rest of the registry still loads on a lean install.
"""
from __future__ import annotations

import importlib
import logging

log = logging.getLogger(__name__)

# Order is irrelevant for registration; grouped by pipeline stage for readability.
_BLOCK_MODULES = [
    "engine.blocks.source",
    "engine.blocks.cut_trim",
    "engine.blocks.silence_trim",
    "engine.blocks.transcribe",
    "engine.blocks.subtitles",
    "engine.blocks.face_blur",
    "engine.blocks.key_moments",
    "engine.blocks.moments_cut",
    "engine.blocks.ai_extract",
    "engine.blocks.ai_text",
    "engine.blocks.ai_subtitles",
    "engine.blocks.narrate_tts",
    "engine.blocks.vocal_separation",
    "engine.blocks.background_music",
    "engine.blocks.vertical_crop",
    "engine.blocks.color_filter",
    "engine.blocks.logo",
    "engine.blocks.intro_outro",
    "engine.blocks.thumbnail",
    "engine.blocks.export",
    "engine.blocks.export_clips",
]


def _load() -> None:
    for mod in _BLOCK_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001 - optional deps may be absent
            log.debug("Block module %s unavailable: %s", mod, exc)


_load()
