from __future__ import annotations

import os
import secrets

from flask import Flask

from config import load_config
from web.job_store import JobStore


def create_app(config_path: str = "config/default_config.toml") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    cfg = load_config(config_path)
    app.config["CR_CONFIG"] = cfg
    app.config["CR_STORE"] = JobStore(cfg.jobs_dir)
    app.config["SECRET_KEY"] = os.environ.get("VIGENX_SECRET_KEY") or secrets.token_hex(32)

    # Publish scheduler (created here, started by run_web.py — not in tests).
    from publishing.scheduler import PublishScheduler
    app.config["CR_SCHEDULER"] = PublishScheduler(
        store_path=os.path.join(cfg.jobs_dir, "schedule.json"), config=cfg)

    from web.routes.api import bp as api_bp
    from web.routes.dashboard import bp as dashboard_bp
    from web.routes.editor import bp as editor_bp
    from web.routes.jobs import bp as jobs_bp
    from web.routes.review import bp as review_bp
    from web.routes.settings import bp as settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(review_bp, url_prefix="/review")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Expose app name to all templates for the ViGenX rebrand.
    @app.context_processor
    def _inject_branding():
        return {"app_name": getattr(cfg, "app_name", "ViGenX")}

    return app
