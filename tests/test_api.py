import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from web import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app()
    # isolate template/job writes from the repo
    app.config["CR_CONFIG"].templates_dir = str(tmp_path / "templates")
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
    created = client.post("/api/schedule",
                          json={"video_path": str(vid), "platform": "folder"}).get_json()
    sid = created["id"]
    listing = client.get("/api/schedule").get_json()["scheduled"]
    assert any(i["id"] == sid for i in listing)
    assert client.delete(f"/api/schedule/{sid}").get_json()["canceled"] is True


def test_schedule_requires_video_path(client):
    r = client.post("/api/schedule", json={"platform": "folder"})
    assert r.status_code == 400


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
