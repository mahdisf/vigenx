import json

from engine.plan_cli import main


def test_plan_cli_writes_valid_graph(tmp_path):
    output = tmp_path / "workflow.json"
    code = main([
        "Create two vertical clips with captions",
        "--mode", "local",
        "--source", "episode.mp4",
        "--output", str(output),
    ])

    assert code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["planner"] == "local"
    assert data["graph"]["meta"]["requires_approval"] is True
    assert any(node["type_id"] == "export_clips" for node in data["graph"]["nodes"])
