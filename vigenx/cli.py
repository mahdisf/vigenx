"""Stable source-checkout CLI for planning, diagnostics, and the local UI."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
from typing import Any, Sequence

from vigenx import __version__


CORE_MODULES = (
    ("Flask", "flask", "pip install -r requirements-core.txt"),
    ("Pydantic", "pydantic", "pip install -r requirements-core.txt"),
    ("python-dotenv", "dotenv", "pip install -r requirements-core.txt"),
    ("Requests", "requests", "pip install -r requirements-core.txt"),
    ("SRT", "srt", "pip install -r requirements-core.txt"),
    ("yt-dlp", "yt_dlp", "pip install -r requirements-core.txt"),
)

RENDER_MODULES = (
    ("MoviePy", "moviepy", "pip install -r requirements.txt"),
    ("OpenCV", "cv2", "pip install -r requirements.txt"),
    ("NumPy", "numpy", "pip install -r requirements.txt"),
    ("Pillow", "PIL", "pip install -r requirements.txt"),
    ("pydub", "pydub", "pip install -r requirements.txt"),
)

AI_MODULES = (
    ("Whisper", "whisper", "pip install -r requirements.txt"),
    ("PyTorch", "torch", "pip install -r requirements.txt"),
    ("Gemini SDK", "google.generativeai", "pip install -r requirements.txt"),
    ("OpenAI client", "openai", "pip install -r requirements.txt"),
)


def _module_available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def doctor_report() -> dict[str, Any]:
    """Return a machine-readable capability report without importing heavy tools."""
    checks: list[dict[str, Any]] = []

    python_ok = sys.version_info >= (3, 10)
    checks.append(
        {
            "name": "Python",
            "group": "core",
            "ok": python_ok,
            "detail": platform.python_version(),
            "hint": "Install Python 3.10 or newer",
        }
    )

    for name, module, hint in CORE_MODULES:
        checks.append(
            {
                "name": name,
                "group": "core",
                "ok": _module_available(module),
                "detail": module,
                "hint": hint,
            }
        )

    try:
        from config import load_config
        from engine.planner import WorkflowPlanner
        from engine.registry import block_schemas, plugin_errors

        plan = WorkflowPlanner(load_config()).plan(
            "Create one vertical clip with captions",
            mode="local",
        )
        plan.graph.validate()
        catalog_count = len(block_schemas())
        discovered_plugin_errors = plugin_errors()
        planner_ok = True
        planner_detail = f"validated graph; {catalog_count} registered blocks"
    except Exception as exc:  # noqa: BLE001 - diagnostics must report, not crash
        discovered_plugin_errors = []
        planner_ok = False
        planner_detail = str(exc)
    checks.append(
        {
            "name": "Local planner",
            "group": "core",
            "ok": planner_ok,
            "detail": planner_detail,
            "hint": "Run the command from the repository root and install requirements-core.txt",
        }
    )

    for executable in ("ffmpeg", "ffprobe"):
        path = shutil.which(executable)
        checks.append(
            {
                "name": executable,
                "group": "render",
                "ok": path is not None,
                "detail": path or "not found on PATH",
                "hint": "Install FFmpeg and add it to PATH",
            }
        )

    for name, module, hint in RENDER_MODULES:
        checks.append(
            {
                "name": name,
                "group": "render",
                "ok": _module_available(module),
                "detail": module,
                "hint": hint,
            }
        )

    for name, module, hint in AI_MODULES:
        checks.append(
            {
                "name": name,
                "group": "ai",
                "ok": _module_available(module),
                "detail": module,
                "hint": hint,
            }
        )

    core = [item for item in checks if item["group"] == "core"]
    render = [item for item in checks if item["group"] == "render"]
    ai = [item for item in checks if item["group"] == "ai"]
    core_ready = all(item["ok"] for item in core)
    render_ready = core_ready and all(item["ok"] for item in render)
    ai_ready = all(item["ok"] for item in ai)
    return {
        "version": __version__,
        "core_ready": core_ready,
        "render_ready": render_ready,
        "ai_ready": ai_ready,
        "full_ready": render_ready and ai_ready,
        "plugin_errors": discovered_plugin_errors,
        "checks": checks,
    }


def _doctor(args: argparse.Namespace) -> int:
    report = doctor_report()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"ViGenX {report['version']} doctor")
        for item in report["checks"]:
            state = "ok" if item["ok"] else "missing"
            print(f"[{state:7}] {item['group']:6} {item['name']}: {item['detail']}")
            if not item["ok"]:
                print(f"          {item['hint']}")
        print(f"Planning/UI ready: {'yes' if report['core_ready'] else 'no'}")
        print(f"Base rendering ready: {'yes' if report['render_ready'] else 'no'}")
        print(f"AI provider SDKs ready: {'yes' if report['ai_ready'] else 'no'}")
        print(f"Full profile ready: {'yes' if report['full_ready'] else 'no'}")
    return 0 if report["full_ready" if args.strict else "core_ready"] else 1


def _plan(args: argparse.Namespace) -> int:
    from engine.plan_cli import main as plan_main

    forwarded = list(args.plan_args)
    if not forwarded:
        forwarded = ["--help"]
    return plan_main(forwarded)


def _web(args: argparse.Namespace) -> int:
    from core.dependency_check import check_dependencies
    from core.logging_setup import configure_logging
    from web import create_app

    configure_logging()
    check_dependencies(raise_on_missing=False)
    app = create_app(args.config)
    cfg = app.config["CR_CONFIG"]
    debug = cfg.flask_debug if args.debug is None else args.debug
    if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        app.config["CR_SCHEDULER"].start()
    app.run(
        host=args.host or cfg.flask_host,
        port=args.port or cfg.flask_port,
        debug=debug,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vigenx",
        description="Plan and inspect agentic video workflows from a source checkout.",
    )
    parser.add_argument("--version", action="version", version=f"ViGenX {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="Check planning and render capabilities")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    doctor.add_argument(
        "--strict",
        action="store_true",
        help="Return failure unless the full render profile is available",
    )
    doctor.set_defaults(handler=_doctor)

    plan = subparsers.add_parser(
        "plan",
        add_help=False,
        help="Compile a plain-language brief into validated workflow JSON",
    )
    plan.add_argument("plan_args", nargs=argparse.REMAINDER)
    plan.set_defaults(handler=_plan)

    web = subparsers.add_parser("web", help="Start the trusted local editor")
    web.add_argument("--config", default="config/default_config.toml")
    web.add_argument("--host")
    web.add_argument("--port", type=int)
    debug = web.add_mutually_exclusive_group()
    debug.add_argument("--debug", dest="debug", action="store_true")
    debug.add_argument("--no-debug", dest="debug", action="store_false")
    web.set_defaults(debug=None, handler=_web)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))


__all__ = ["build_parser", "doctor_report", "main"]
