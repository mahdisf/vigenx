import json
from pathlib import Path

import pytest

from config import AppConfig
from engine.graph import PipelineGraph
from engine.planner import WorkflowPlanner
from engine.registry import load_builtin_blocks


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "workflows"
CASES = (
    (
        "podcast-shorts.json",
        "Create three vertical podcast clips under 45 seconds with yellow captions and background music.",
        "media/podcast.mp4",
    ),
    (
        "privacy-highlight.json",
        "Make one privacy-safe highlight reel under 45 seconds, blur faces, and add captions.",
        "media/interview.mp4",
    ),
    (
        "branded-reel.json",
        "Make a cinematic vertical branded reel with a logo, intro, outro, background music, and a thumbnail.",
        "media/product-demo.mp4",
    ),
)


@pytest.mark.parametrize("filename,brief,source", CASES, ids=lambda value: value)
def test_committed_workflow_example_matches_local_planner(filename, brief, source):
    load_builtin_blocks()
    path = EXAMPLES / filename
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["planner"] == "local"
    assert payload["summary"].startswith("Built a validated workflow:")
    assert payload["graph"]["id"] == f"example-{path.stem}"
    assert payload["graph"]["meta"]["requires_approval"] is True

    graph = PipelineGraph.from_dict(payload["graph"])
    graph.validate()
    assert graph.topological_order()
    assert any(node.type_id in {"export", "export_clips"} for node in graph.nodes)

    regenerated = WorkflowPlanner(AppConfig()).plan(
        brief,
        source=source,
        mode="local",
    ).to_dict()
    regenerated["graph"]["id"] = payload["graph"]["id"]
    assert regenerated == payload


def test_workflow_examples_are_present():
    assert {path.name for path in EXAMPLES.glob("*.json")} == {
        "branded-reel.json",
        "podcast-shorts.json",
        "privacy-highlight.json",
    }
