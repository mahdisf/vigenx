from flask import Blueprint, current_app, redirect, render_template, url_for

bp = Blueprint("review", __name__)


@bp.get("/")
def index():
    store = current_app.config["CR_STORE"]
    pending = [j for j in store.list_all() if j.status == "awaiting_review"]
    return render_template("review.html", jobs=pending)


@bp.post("/<job_id>/approve")
def approve(job_id: str):
    store = current_app.config["CR_STORE"]
    if store.exists(job_id):
        job = store.load(job_id)
        job.status = "approved"
        store.save(job)
    return redirect(url_for("review.index"))


@bp.post("/<job_id>/reject")
def reject(job_id: str):
    store = current_app.config["CR_STORE"]
    if store.exists(job_id):
        job = store.load(job_id)
        job.status = "rejected"
        store.save(job)
    return redirect(url_for("review.index"))
