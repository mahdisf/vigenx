import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from web import create_app
from publishing.scheduler import PublishScheduler
from web.job_store import Job, JobStore


@pytest.fixture()
def client(tmp_path):
    app = create_app()
    # isolate template/job writes from the repo
    app.config["CR_CONFIG"].templates_dir = str(tmp_path / "templates")
    app.config["CR_STORE"] = JobStore(str(tmp_path / "jobs"))
    app.config["CR_SCHEDULER"] = PublishScheduler(
        store_path=str(tmp_path / "schedule.json"),
        config=app.config["CR_CONFIG"],
    )
    yield app.test_client()


def test_blocks_endpoint(client):
    data = client.get("/api/blocks").get_json()
    ids = {b["type_id"] for b in data["blocks"]}
    assert {"source", "subtitles", "export"} <= ids
    # schema carries inputs/outputs/params + preview_kind
    subs = next(b for b in data["blocks"] if b["type_id"] == "subtitles")
    assert subs["preview_kind"] == "frame"
    assert any(p["name"] == "color" for p in subs["params"])


def test_editor_page(client):
    r = client.get("/editor")
    assert r.status_code == 200
    assert b"vx-root" in r.data and b"editor.js" in r.data


def test_template_crud(client):
    graph = {
        "id": "t_api", "name": "API Test",
        "nodes": [
            {"id": "s", "type_id": "source", "params": {"source": "x.mp4"}},
            {"id": "o", "type_id": "export", "params": {}},
        ],
        "edges": [{"source": "s", "source_port": "media", "target": "o", "target_port": "media"}],
    }
    assert client.post("/api/templates", json=graph).get_json()["id"] == "t_api"
    loaded = client.get("/api/templates/t_api").get_json()
    assert loaded["name"] == "API Test" and len(loaded["nodes"]) == 2
    assert client.delete("/api/templates/t_api").get_json()["deleted"] is True
    assert client.get("/api/templates/t_api").status_code == 404


def test_sources_resolve_local(client, tmp_path):
    (tmp_path / "v1.mp4").write_bytes(b"x")
    (tmp_path / "v2.mp4").write_bytes(b"x")
    data = client.post("/api/sources/resolve",
                       json={"source": str(tmp_path / "*.mp4"), "source_type": "local"}).get_json()
    assert len(data["items"]) == 2


def test_uploaders_endpoint(client):
    data = client.get("/api/uploaders").get_json()["uploaders"]
    by = {u["platform"]: u for u in data}
    assert by["folder"]["available"] is True


def test_schedule_crud(client, tmp_path):
    vid = tmp_path / "s.mp4"
    vid.write_bytes(b"x")
    job = Job(status="approved", output_path=str(vid))
    client.application.config["CR_STORE"].save(job)
    created = client.post("/api/schedule",
                          json={"job_id": job.id, "video_path": str(vid),
                                "platform": "folder"}).get_json()
    sid = created["id"]
    assert created["job_id"] == job.id
    listing = client.get("/api/schedule").get_json()["scheduled"]
    assert any(i["id"] == sid for i in listing)
    assert client.delete(f"/api/schedule/{sid}").get_json()["canceled"] is True


def test_schedule_requires_video_path(client):
    r = client.post("/api/schedule", json={"platform": "folder"})
    assert r.status_code == 400


def test_schedule_requires_job_id(client, tmp_path):
    video = str(tmp_path / "clip.mp4")
    response = client.post("/api/schedule", json={"video_path": video})
    assert response.status_code == 400
    assert response.get_json()["error"] == "job_id is required"


def test_schedule_rejects_unknown_or_unapproved_job(client, tmp_path):
    video = str(tmp_path / "clip.mp4")
    missing = client.post(
        "/api/schedule",
        json={"job_id": "missing", "video_path": video},
    )
    assert missing.status_code == 404

    job = Job(status="awaiting_review", output_path=video)
    client.application.config["CR_STORE"].save(job)
    unapproved = client.post(
        "/api/schedule",
        json={"job_id": job.id, "video_path": video},
    )
    assert unapproved.status_code == 409
    assert "approved" in unapproved.get_json()["error"]


def test_schedule_rejects_path_not_owned_by_job(client, tmp_path):
    approved = str(tmp_path / "approved.mp4")
    unrelated = str(tmp_path / "unrelated.mp4")
    job = Job(status="approved", outputs=[approved])
    client.application.config["CR_STORE"].save(job)

    response = client.post(
        "/api/schedule",
        json={"job_id": job.id, "video_path": unrelated},
    )

    assert response.status_code == 400
    assert "not an output" in response.get_json()["error"]


def test_validate_endpoint_ok(client):
    graph = {
        "name": "v",
        "nodes": [{"id": "s", "type_id": "source", "params": {"source": "x.mp4"}},
                  {"id": "c", "type_id": "cut_trim", "params": {}}],
        "edges": [{"source": "s", "source_port": "media", "target": "c", "target_port": "media"}],
    }
    assert client.post("/api/validate", json={"graph": graph}).get_json()["ok"] is True


def test_validate_endpoint_reports_type_mismatch(client):
    # transcribe outputs SUBTITLES; feeding that into cut_trim's MEDIA input is invalid
    graph = {
        "name": "bad",
        "nodes": [{"id": "s", "type_id": "source", "params": {"source": "x.mp4"}},
                  {"id": "a", "type_id": "transcribe", "params": {}},
                  {"id": "c", "type_id": "cut_trim", "params": {}}],
        "edges": [{"source": "s", "source_port": "media", "target": "a", "target_port": "media"},
                  {"source": "a", "source_port": "subtitles", "target": "c", "target_port": "media"}],
    }
    out = client.post("/api/validate", json={"graph": graph}).get_json()
    assert out["ok"] is False and "mismatch" in out["error"].lower()


def test_run_requires_graph(client, monkeypatch):
    started = []
    monkeypatch.setattr("web.worker.run_job", lambda *args: started.append(args))

    response = client.post("/api/run", json={})

    assert response.status_code == 400
    assert "graph is required" in response.get_json()["error"]
    assert started == []


def test_run_rejects_invalid_graph_before_creating_job(client, monkeypatch):
    started = []
    monkeypatch.setattr("web.worker.run_job", lambda *args: started.append(args))

    response = client.post("/api/run", json={"graph": {"nodes": [], "edges": []}})

    assert response.status_code == 400
    assert "no nodes" in response.get_json()["error"].lower()
    assert started == []


def test_run_starts_validated_graph_job(client, monkeypatch):
    started = []
    monkeypatch.setattr("web.worker.run_job", lambda *args: started.append(args))
    graph = {
        "name": "valid run",
        "nodes": [
            {"id": "s", "type_id": "source", "params": {"source": "x.mp4"}},
            {"id": "o", "type_id": "export", "params": {}},
        ],
        "edges": [{"source": "s", "source_port": "media", "target": "o", "target_port": "media"}],
    }

    response = client.post("/api/run", json={"graph": graph})

    assert response.status_code == 200
    assert response.get_json()["job_id"]
    assert len(started) == 1
    assert started[0][0].graph["name"] == "valid run"


def test_agent_plan_endpoint_returns_valid_editable_graph(client):
    response = client.post(
        "/api/agent/plan",
        json={
            "brief": "Create three vertical clips with captions",
            "source": "episode.mp4",
            "mode": "local",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["planner"] == "local"
    assert data["graph"]["meta"]["requires_approval"] is True
    assert any(node["type_id"] == "export_clips" for node in data["graph"]["nodes"])
    assert client.post("/api/validate", json={"graph": data["graph"]}).get_json()["ok"] is True


def test_agent_plan_endpoint_rejects_empty_brief(client):
    response = client.post("/api/agent/plan", json={"brief": "", "mode": "local"})
    assert response.status_code == 400
    assert "describe" in response.get_json()["error"].lower()
