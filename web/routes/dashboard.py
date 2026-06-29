from flask import Blueprint, current_app, render_template

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def index():
    store = current_app.config["CR_STORE"]
    jobs = store.list_all()
    return render_template("dashboard.html", jobs=jobs)
