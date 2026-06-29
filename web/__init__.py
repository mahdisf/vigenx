from __future__ import annotations

from flask import Flask

from config import load_config
from web.job_store import JobStore


def create_app(config_path: str = "config/default_config.toml") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    cfg = load_config(config_path)
    app.config["CR_CONFIG"] = cfg
    app.config["CR_STORE"] = JobStore(cfg.jobs_dir)
    app.config["SECRET_KEY"] = "change-me-in-production"

    from web.routes.dashboard import bp as dashboard_bp
    from web.routes.jobs import bp as jobs_bp
    from web.routes.review import bp as review_bp
    from web.routes.settings import bp as settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(review_bp, url_prefix="/review")
    app.register_blueprint(settings_bp, url_prefix="/settings")

    return app
