from TTS.api import TTS as TTS_API
from typing import Optional

def T_T_S(
    text: str,
    file_path: str,
    model_name: str = "tts_models/en/vctk/vits",
    speaker: Optional[str] = "p339",
    language: Optional[str] = "en",
    speaker_wav: Optional[str] = None
) -> None:
    """
    Converts text to speech and saves it to a WAV file.

    Args:
        text (str): The text to convert to speech.
        file_path (str): Output path for the WAV file.
        model_name (str, optional): TTS model to use. Defaults to "tts_models/en/vctk/vits".
        speaker (str, optional): Speaker ID for multi-speaker models. Defaults to "p339".
        language (str, optional): Language code for multi-lingual models. Defaults to "en".
        speaker_wav (str, optional): Path to reference speaker WAV file for style transfer. Defaults to None.

    Returns:
        None
    """
    # Initialize TTS model
    tts = TTS_API(model_name)

    # Generate speech
    tts.tts_to_file(
        text=text,
        speaker=speaker,
        # language=language,
        # speaker_wav=speaker_wav,
        file_path=file_path
    )

    print(f"✅ Speech saved to {file_path}")
