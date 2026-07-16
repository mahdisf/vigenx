"""Serves the React Flow pipeline editor page."""
from flask import Blueprint, render_template

bp = Blueprint("editor", __name__)


@bp.get("/editor")
def index():
    return render_template("editor.html", template_id="")


@bp.get("/editor/<template_id>")
def edit(template_id: str):
    return render_template("editor.html", template_id=template_id)
