"""JSON API powering the React Flow editor.

Endpoints:
  GET    /api/blocks                 block schemas (palette + inspector source of truth)
  GET    /api/templates              list saved templates
  GET    /api/templates/<id>         load one template graph
  POST   /api/templates              save (create/update) a template graph
  DELETE /api/templates/<id>         delete a template
  POST   /api/sources/resolve        enumerate selectable media references
  POST   /api/preview/frame          composited preview frame (JPEG) at a node
  POST   /api/preview/draft          short low-res draft render (MP4) of the graph
  POST   /api/run                    submit a batch graph run -> job id
"""
from __future__ import annotations

import logging
import os
import string

from flask import Blueprint, abort, current_app, jsonify, request, send_file, url_for

log = logging.getLogger(__name__)
bp = Blueprint("api", __name__)


def _cfg():
    return current_app.config["CR_CONFIG"]


# --- filesystem browser (for file/folder Browse fields) -----------------------
@bp.get("/fs/list")
def fs_list():
    """List a directory on the server so the editor's Browse fields can pick a path.

    Query params: ``path`` (blank = drive roots / filesystem root) and optional
    ``exts`` (comma-separated extensions to keep, e.g. ``mp4,mov``).
    """
    path = (request.args.get("path") or "").strip()
    exts = [e.strip().lower().lstrip(".") for e in (request.args.get("exts") or "").split(",") if e.strip()]

    # No path -> top level: Windows drive roots, else the filesystem root.
    if not path:
        if os.name == "nt":
            roots = [f"{d}:\\" for d in string.ascii_uppercase if os.path.isdir(f"{d}:\\")]
            dirs = [{"name": r, "path": r} for r in roots]
            return jsonify({"cwd": "", "parent": None, "dirs": dirs, "files": []})
        path = "/"

    path = os.path.abspath(path)
    if not os.path.isdir(path):
        return jsonify({"error": f"Not a directory: {path}"}), 400

    dirs, files = [], []
    try:
        for name in sorted(os.listdir(path), key=str.lower):
            full = os.path.join(path, name)
            try:
                if os.path.isdir(full):
                    dirs.append({"name": name, "path": full})
                elif os.path.isfile(full):
                    if exts and name.rsplit(".", 1)[-1].lower() not in exts:
                        continue
                    files.append({"name": name, "path": full})
            except OSError:
                continue  # unreadable entry (permissions, broken link)
    except OSError as exc:
        return jsonify({"error": str(exc)}), 400

    parent = os.path.dirname(path)
    if parent == path:  # at a drive/filesystem root -> parent is the roots listing
        parent = ""
    return jsonify({"cwd": path, "parent": parent, "dirs": dirs, "files": files})


# --- system fonts (for the Font dropdown) -------------------------------------
@bp.get("/fonts")
def fonts():
    return jsonify({"fonts": _list_fonts(_cfg())})


def _list_fonts(cfg) -> list:
    names = set()
    # Project fonts folder first.
    fonts_dir = getattr(cfg, "fonts_dir", "")
    for root in (fonts_dir, r"C:\Windows\Fonts"):
        if root and os.path.isdir(root):
            for fn in os.listdir(root):
                if fn.lower().endswith((".ttf", ".otf", ".ttc")):
                    names.add(os.path.splitext(fn)[0])
    # Family names via matplotlib if available (nicer than filenames).
    try:
        from matplotlib import font_manager  # type: ignore[import]

        for f in font_manager.fontManager.ttflist:
            if f.name:
                names.add(f.name)
    except Exception as exc:  # best-effort
        log.debug("matplotlib font enumeration unavailable: %s", exc)
    return sorted(names, key=str.lower)


# --- blocks -------------------------------------------------------------------
@bp.get("/blocks")
def blocks():
    import engine

    engine.load_builtin_blocks()
    return jsonify({"blocks": engine.block_schemas()})


# --- templates ----------------------------------------------------------------
@bp.get("/templates")
def list_templates():
    from engine.templates import list_templates as _list

    return jsonify({"templates": _list(_cfg().templates_dir)})


@bp.get("/templates/<template_id>")
def get_template(template_id: str):
    from engine.templates import load_template

    try:
        graph = load_template(template_id, _cfg().templates_dir)
    except FileNotFoundError:
        abort(404)
    return jsonify(graph.to_dict())


@bp.post("/templates")
def save_template():
    from engine.graph import PipelineGraph
    from engine.templates import save_template as _save

    data = request.get_json(force=True, silent=True) or {}
    graph = PipelineGraph.from_dict(data)
    if not graph.name or graph.name == "Untitled":
        graph.name = data.get("name") or graph.name
    _save(graph, _cfg().templates_dir)
    return jsonify({"id": graph.id, "name": graph.name})


@bp.post("/validate")
def validate_graph():
    from engine.graph import PipelineGraph

    data = request.get_json(force=True, silent=True) or {}
    graph_data = data.get("graph", data)
    try:
        PipelineGraph.from_dict(graph_data).validate()
        return jsonify({"ok": True})
    except Exception as exc:  # noqa: BLE001 - report message to the editor
        return jsonify({"ok": False, "error": str(exc)})


@bp.delete("/templates/<template_id>")
def delete_template(template_id: str):
    from engine.templates import delete_template as _delete

    ok = _delete(template_id, _cfg().templates_dir)
    return jsonify({"deleted": ok})


# --- sources ------------------------------------------------------------------
@bp.post("/sources/resolve")
def resolve_sources():
    from sources.resolver import resolve

    data = request.get_json(force=True, silent=True) or {}
    items = resolve(data.get("source", ""), data.get("source_type", "auto"))
    return jsonify({"items": [r.to_dict() for r in items]})


# --- preview ------------------------------------------------------------------
@bp.post("/preview/frame")
def preview_frame():
    from engine.executor import GraphExecutor
    from engine.graph import PipelineGraph
    from engine.ports import ImageRef, MediaRef

    data = request.get_json(force=True, silent=True) or {}
    try:
        graph = PipelineGraph.from_dict(data["graph"])
        node_id = data["node_id"]
        t = float(data.get("t", 1.0))
        overrides = data.get("overrides") or {}
        executor = GraphExecutor(graph, _cfg())
        result = executor.preview_at(node_id, t=t, param_overrides=overrides)
    except Exception as exc:  # noqa: BLE001
        log.exception("preview/frame failed")
        return jsonify({"error": str(exc)}), 400

    path = getattr(result, "path", None)
    if not path:
        return jsonify({"error": "block produced no previewable frame"}), 400
    return send_file(path, mimetype="image/jpeg")


@bp.post("/preview/draft")
def preview_draft():
    from engine.executor import GraphExecutor
    from engine.graph import PipelineGraph

    data = request.get_json(force=True, silent=True) or {}
    try:
        graph = PipelineGraph.from_dict(data["graph"])
        node_id = data.get("node_id")
        overrides = data.get("overrides") or {}
        executor = GraphExecutor(graph, _cfg())
        result = executor.draft(node_id=node_id, param_overrides=overrides)
        paths = result.media_paths()
    except Exception as exc:  # noqa: BLE001
        log.exception("preview/draft failed")
        return jsonify({"error": str(exc)}), 400

    if not paths:
        return jsonify({"error": "graph produced no draft output"}), 400
    return send_file(paths[0], mimetype="video/mp4")


# --- uploaders & scheduling ---------------------------------------------------
@bp.get("/uploaders")
def uploaders():
    from output.uploaders import uploader_status

    return jsonify({"uploaders": uploader_status(_cfg())})


def _scheduler():
    return current_app.config.get("CR_SCHEDULER")


@bp.get("/schedule")
def list_schedule():
    from dataclasses import asdict

    sched = _scheduler()
    if not sched:
        return jsonify({"scheduled": []})
    return jsonify({"scheduled": [asdict(i) for i in sched.list_all()]})


@bp.post("/schedule")
def add_schedule():
    from dataclasses import asdict

    sched = _scheduler()
    if not sched:
        return jsonify({"error": "scheduler unavailable"}), 503
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("video_path"):
        return jsonify({"error": "video_path is required"}), 400
    fields = {k: data[k] for k in (
        "video_path", "platform", "publish_at", "recurrence",
        "title", "description", "tags", "privacy") if k in data}
    item = sched.add(**fields)
    return jsonify(asdict(item))


@bp.delete("/schedule/<item_id>")
def cancel_schedule(item_id: str):
    sched = _scheduler()
    if not sched:
        return jsonify({"error": "scheduler unavailable"}), 503
    return jsonify({"canceled": sched.cancel(item_id)})


@bp.post("/schedule/run_due")
def run_due_schedule():
    from dataclasses import asdict

    sched = _scheduler()
    if not sched:
        return jsonify({"error": "scheduler unavailable"}), 503
    fired = sched.run_due()
    return jsonify({"fired": [asdict(i) for i in fired]})


# --- run ----------------------------------------------------------------------
@bp.post("/run")
def run():
    from web.job_store import Job
    from web.worker import run_job

    store = current_app.config["CR_STORE"]
    cfg = _cfg()
    data = request.get_json(force=True, silent=True) or {}

    job = Job(
        pipeline_type="graph",
        graph=data.get("graph"),
        template_id=data.get("template_id"),
        source_refs=data.get("source_refs") or [],
    )
    store.save(job)
    run_job(job, cfg, store)
    return jsonify({"job_id": job.id, "url": url_for("jobs.detail", job_id=job.id)})
