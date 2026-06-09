from typing import Optional


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
    Converts text to speech and saves it to an audio file.

    The default engine is pyttsx3 because Coqui TTS currently conflicts with
    mediapipe in the main environment through incompatible protobuf ranges.
    Use engine="coqui" only in an environment where Coqui TTS is installed.
    """
    if engine == "coqui":
        try:
            from TTS.api import TTS as TTS_API
        except ImportError as exc:
            raise RuntimeError(
                "Coqui TTS is not installed. Install requirements-coqui-tts.txt "
                "in a separate environment because it conflicts with mediapipe."
            ) from exc

        tts = TTS_API(model_name)
        tts.tts_to_file(
            text=text,
            speaker=speaker,
            # language=language,
            # speaker_wav=speaker_wav,
            file_path=file_path,
        )
    elif engine == "pyttsx3":
        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError("pyttsx3 is not installed. Run: pip install pyttsx3") from exc

        tts = pyttsx3.init()
        tts.save_to_file(text, file_path)
        tts.runAndWait()
    else:
        raise ValueError(f"Unsupported TTS engine: {engine}")

    print(f"Speech saved to {file_path}")


# Backward-compatible alias for older scripts.
T_T_S = text_to_speech
