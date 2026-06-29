#!/usr/bin/env python3
"""Entry point for the Content-Regenerator web UI.

    python run_web.py
    # then open http://127.0.0.1:5000
"""
from core.dependency_check import check_dependencies
from core.logging_setup import configure_logging
from web import create_app

configure_logging()
check_dependencies(raise_on_missing=False)

app = create_app()

if __name__ == "__main__":
    cfg = app.config["CR_CONFIG"]
    app.run(host=cfg.flask_host, port=cfg.flask_port, debug=cfg.flask_debug)
