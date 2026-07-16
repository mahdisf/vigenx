import json
import time

from flask import (
    Blueprint, Response, current_app, redirect,
    render_template, request, url_for,
)

from web.job_store import Job, TERMINAL_STATUSES
from web.worker import run_job

bp = Blueprint("jobs", __name__)


@bp.get("/new")
def new():
    return render_template("job_new.html")


@bp.post("/")
def create():
    store = current_app.config["CR_STORE"]
    cfg = current_app.config["CR_CONFIG"]

    source_type = request.form.get("source_type", "local")
    source = request.form.get("source", "").strip()
    pipeline_type = request.form.get("pipeline_type", "general")

    options: dict = {}
    if pipeline_type == "game":
        options["game_name"] = request.form.get("game_name", cfg.game_name)
        auto = request.form.get("auto_mode", "1")
        options["auto_mode"] = auto not in ("0", "false", "no")
    if pipeline_type == "speaker":
        options["whisper_model"] = request.form.get("whisper_model", cfg.whisper_model)
        options["blur_faces"] = "blur_faces" in request.form
        options["no_music"] = "no_music" in request.form
    if pipeline_type == "general":
        options["whisper"] = "whisper" in request.form
        options["trim_silence"] = "trim_silence" in request.form
        options["blur_faces"] = "blur_faces" in request.form

    job = Job(
        pipeline_type=pipeline_type,
        source_type=source_type,
        source=source,
        options=options,
    )
    store.save(job)
    run_job(job, cfg, store)
    return redirect(url_for("jobs.detail", job_id=job.id))


@bp.get("/<job_id>")
def detail(job_id: str):
    store = current_app.config["CR_STORE"]
    if not store.exists(job_id):
        return "Job not found", 404
    job = store.load(job_id)
    return render_template("job_detail.html", job=job)


@bp.get("/<job_id>/stream")
def stream(job_id: str):
    """Server-Sent Events endpoint for live job progress."""
    store = current_app.config["CR_STORE"]

    def event_gen():
        while True:
            if not store.exists(job_id):
                yield "data: {\"error\": \"job not found\"}\n\n"
                return
            job = store.load(job_id)
            payload = json.dumps({
                "status": job.status,
                "progress_pct": job.progress_pct,
                "log_tail": job.log_lines[-10:] if job.log_lines else [],
                "node_status": job.node_status,
                "output_path": job.output_path,
                "error_message": job.error_message,
            })
            yield f"data: {payload}\n\n"
            if job.status in TERMINAL_STATUSES:
                return
            time.sleep(2)

    return Response(event_gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
