from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


@dataclass
class AppConfig:
    # --- Paths ---
    input_dir: str = "downloads"
    output_dir: str = "output"
    music_folder: str = "musics"
    fonts_dir: str = "fonts"
    speaker_input_dir: str = "speaker-downloads"
    speaker_output_dir: str = "speaker-output"
    clips_dir: str = "clips"
    jobs_dir: str = "jobs"

    # --- Video parameters ---
    max_duration: int = 59
    fade_duration: float = 0.5
    transition_duration: float = 0.3
    output_fps: int = 30
    crf: int = 18
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    preset: str = "medium"

    # --- Game pipeline defaults ---
    game_name: str = "Counter-Strike"
    yolo_model: str = "yolov8n.pt"
    use_gpu_encoder: bool = False

    # --- Speaker pipeline defaults ---
    whisper_model: str = "small"
    music_volume: float = 0.15
    voice_volume: float = 0.8

    # --- Gemini ---
    gemini_text_model: str = "gemini-2.5-flash"
    gemini_video_model: str = "gemini-2.5-flash"

    # --- TTS ---
    tts_engine: str = "pyttsx3"
    tts_model: str = "tts_models/en/vctk/vits"
    tts_speaker: str = "p339"

    # --- ImageMagick (Windows default path) ---
    imagemagick_binary: str = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

    # --- Text overlay styling ---
    text_color: str = "white"
    text_stroke_color: str = "#FD3C9D"
    text_shadow: bool = True
    text_shadow_color: str = "#000000"
    text_shadow_offset: int = 4

    # --- Video color filters (1.0 = no change) ---
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.1

    # --- Branding ---
    logo_path: str = ""           # path to a PNG logo; empty = no logo
    logo_position: str = "top-right"   # top-left | top-right | bottom-left | bottom-right
    logo_opacity: float = 0.85
    logo_scale: float = 0.10      # fraction of video width

    # --- Intro / outro clips ---
    intro_clip: str = ""          # path to an MP4 to prepend; empty = none
    outro_clip: str = ""          # path to an MP4 to append; empty = none

    # --- History spreadsheet ---
    history_csv: str = "output/history.csv"

    # --- Flask web ---
    flask_host: str = "127.0.0.1"
    flask_port: int = 5000
    flask_debug: bool = False

    # --- API keys: read from env vars only, never stored in TOML ---
    google_api_key: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_API_KEY", "")
    )
    twitch_client_id: str = field(
        default_factory=lambda: os.environ.get("TWITCH_CLIENT_ID", "")
    )
    twitch_client_secret: str = field(
        default_factory=lambda: os.environ.get("TWITCH_CLIENT_SECRET", "")
    )


def load_config(config_path: str = "config/default_config.toml") -> AppConfig:
    """Load AppConfig from a TOML or YAML file. Missing file returns defaults."""
    cfg = AppConfig()
    if not os.path.isfile(config_path):
        return cfg

    ext = os.path.splitext(config_path)[1].lower()
    data: dict = {}

    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import]
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except ImportError:
            raise RuntimeError(
                "PyYAML is required for YAML configs. Run: pip install pyyaml"
            )
    else:
        if tomllib is None:
            return cfg
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

    for k, v in data.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    return cfg
