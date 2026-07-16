from __future__ import annotations

import json
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

    # --- LLM providers (model is chosen per block; keys from Settings/env) ---
    llm_provider: str = "gemini"  # default provider for new AI blocks
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

    # --- ViGenX branding / graph engine ---
    app_name: str = "ViGenX"
    logo_asset: str = "assets/logo.png"      # brand logo shown in the web UI
    templates_dir: str = "templates"         # saved pipeline graph templates (JSON)
    renders_dir: str = "renders"             # organized output render tree
    credentials_dir: str = "credentials"     # OAuth tokens / cookies (gitignored)

    # --- Flask web ---
    flask_host: str = "127.0.0.1"
    flask_port: int = 5000
    flask_debug: bool = False

    # --- API keys: read from env vars or the gitignored credentials store ---
    # (never written to the TOML config file). Environment variables win.
    google_api_key: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_API_KEY", "")
    )
    groq_api_key: str = field(
        default_factory=lambda: os.environ.get("GROQ_API_KEY", "")
    )
    nvidia_api_key: str = field(
        default_factory=lambda: os.environ.get("NVIDIA_API_KEY", "")
    )
    twitch_client_id: str = field(
        default_factory=lambda: os.environ.get("TWITCH_CLIENT_ID", "")
    )
    twitch_client_secret: str = field(
        default_factory=lambda: os.environ.get("TWITCH_CLIENT_SECRET", "")
    )


# Provider key -> AppConfig attribute. Used by the Settings UI and the key store.
LLM_KEY_FIELDS = {
    "gemini": "google_api_key",
    "groq": "groq_api_key",
    "nvidia": "nvidia_api_key",
}


def _llm_keys_path(credentials_dir: str) -> str:
    return os.path.join(credentials_dir, "llm_keys.json")


def load_llm_keys(credentials_dir: str) -> dict:
    """Load stored provider keys (``{provider: key}``); missing file -> ``{}``."""
    path = _llm_keys_path(credentials_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, str)}
    except (OSError, ValueError):
        return {}


def save_llm_keys(credentials_dir: str, keys: dict) -> None:
    """Persist non-empty provider keys to the gitignored credentials store."""
    os.makedirs(credentials_dir, exist_ok=True)
    path = _llm_keys_path(credentials_dir)
    existing = load_llm_keys(credentials_dir)
    for provider, key in keys.items():
        if provider not in LLM_KEY_FIELDS:
            continue
        if key:  # only overwrite when a value is supplied
            existing[provider] = key
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def apply_llm_keys(cfg: "AppConfig") -> None:
    """Fill any provider key not already set via env from the credentials store."""
    stored = load_llm_keys(cfg.credentials_dir)
    for provider, attr in LLM_KEY_FIELDS.items():
        if not getattr(cfg, attr, "") and stored.get(provider):
            setattr(cfg, attr, stored[provider])


def load_config(config_path: str = "config/default_config.toml") -> AppConfig:
    """Load AppConfig from a TOML or YAML file. Missing file returns defaults."""
    cfg = AppConfig()
    if not os.path.isfile(config_path):
        apply_llm_keys(cfg)
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
            apply_llm_keys(cfg)
            return cfg
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

    for k, v in data.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    apply_llm_keys(cfg)
    return cfg
