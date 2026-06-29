from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)


def text_to_speech(
    text: str,
    file_path: str,
    model_name: str = "tts_models/en/vctk/vits",
    speaker: Optional[str] = "p339",
    language: Optional[str] = "en",
    speaker_wav: Optional[str] = None,
    engine: str = "pyttsx3",
) -> None:
    """
    Convert text to speech and save to file_path.

    Default engine is pyttsx3 because Coqui TTS conflicts with mediapipe
    via incompatible protobuf versions. Use engine='coqui' only in a
    separate environment where requirements-coqui-tts.txt is installed.
    """
    if engine == "coqui":
        try:
            from TTS.api import TTS as TTS_API  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "Coqui TTS is not installed. Install requirements-coqui-tts.txt "
                "in a separate environment — it conflicts with mediapipe."
            ) from exc
        tts = TTS_API(model_name)
        tts.tts_to_file(text=text, speaker=speaker, file_path=file_path)

    elif engine == "pyttsx3":
        try:
            import pyttsx3  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("pyttsx3 is not installed. Run: pip install pyttsx3") from exc
        engine_obj = pyttsx3.init()
        engine_obj.save_to_file(text, file_path)
        engine_obj.runAndWait()

    else:
        raise ValueError(f"Unsupported TTS engine: {engine!r}. Use 'pyttsx3' or 'coqui'.")

    log.info("Speech saved to %s", file_path)


# Backward-compatible alias
T_T_S = text_to_speech
