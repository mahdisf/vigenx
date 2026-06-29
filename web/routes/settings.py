import os

from flask import Blueprint, current_app, redirect, render_template, request, url_for

bp = Blueprint("settings", __name__)

# Fields editable via the UI (non-secret, non-path-traversal)
EDITABLE_FIELDS = [
    "game_name", "whisper_model", "tts_engine", "max_duration",
    "music_volume", "voice_volume", "use_gpu_encoder",
    "gemini_text_model", "flask_host", "flask_port", "flask_debug",
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
    return render_template("settings.html", fields=fields, env_keys=env_keys)


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
