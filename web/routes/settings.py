import os

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from config import LLM_KEY_FIELDS, save_llm_keys

bp = Blueprint("settings", __name__)

# Fields editable via the UI (non-secret, non-path-traversal)
EDITABLE_FIELDS = [
    "game_name", "whisper_model", "tts_engine", "max_duration",
    "music_volume", "voice_volume", "use_gpu_encoder",
    "llm_provider", "gemini_text_model", "flask_host", "flask_port", "flask_debug",
]


@bp.get("/")
def index():
    cfg = current_app.config["CR_CONFIG"]
    fields = {k: getattr(cfg, k) for k in EDITABLE_FIELDS}
    env_keys = {
        "GOOGLE_API_KEY": bool(os.environ.get("GOOGLE_API_KEY")),
        "TWITCH_CLIENT_ID": bool(os.environ.get("TWITCH_CLIENT_ID")),
        "TWITCH_CLIENT_SECRET": bool(os.environ.get("TWITCH_CLIENT_SECRET")),
    }
    # AI/LLM provider keys: show which are configured (env or stored), and whether
    # the value is locked by an environment variable (env overrides stored keys).
    llm_env = {"gemini": "GOOGLE_API_KEY", "groq": "GROQ_API_KEY", "nvidia": "NVIDIA_API_KEY"}
    llm_keys = {
        provider: {
            "set": bool(getattr(cfg, attr, "")),
            "env_locked": bool(os.environ.get(llm_env[provider])),
        }
        for provider, attr in LLM_KEY_FIELDS.items()
    }
    return render_template(
        "settings.html", fields=fields, env_keys=env_keys, llm_keys=llm_keys
    )


@bp.post("/")
def save():
    cfg = current_app.config["CR_CONFIG"]
    for key in EDITABLE_FIELDS:
        val = request.form.get(key)
        if val is None:
            continue
        current_type = type(getattr(cfg, key))
        if current_type is bool:
            setattr(cfg, key, val.lower() in ("1", "true", "yes", "on"))
        elif current_type is int:
            try:
                setattr(cfg, key, int(val))
            except ValueError:
                pass
        elif current_type is float:
            try:
                setattr(cfg, key, float(val))
            except ValueError:
                pass
        else:
            setattr(cfg, key, val)
    return redirect(url_for("settings.index"))


@bp.post("/llm_keys")
def save_keys():
    """Persist AI/LLM provider API keys to the gitignored credentials store and
    update the live config. Environment variables still take precedence."""
    cfg = current_app.config["CR_CONFIG"]
    submitted = {}
    for provider, attr in LLM_KEY_FIELDS.items():
        val = (request.form.get(f"key_{provider}") or "").strip()
        if val:
            submitted[provider] = val
            if not os.environ.get(_env_name(provider)):
                setattr(cfg, attr, val)  # live update unless env-locked
    if submitted:
        save_llm_keys(cfg.credentials_dir, submitted)
    return redirect(url_for("settings.index"))


def _env_name(provider: str) -> str:
    return {"gemini": "GOOGLE_API_KEY", "groq": "GROQ_API_KEY",
            "nvidia": "NVIDIA_API_KEY"}[provider]
