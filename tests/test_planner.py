import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import AppConfig
from engine.planner import WorkflowPlanner, WorkflowPlanningError


def _types(plan):
    return [node.type_id for node in plan.graph.nodes]


def test_local_planner_builds_multi_clip_vertical_workflow():
    plan = WorkflowPlanner(AppConfig()).plan(
        "Turn this podcast into three vertical clips with yellow captions and music",
        source="talk.mp4",
        mode="local",
    )

    plan.graph.validate()
    types = _types(plan)
    assert types.count("source") == 1
    assert {"transcribe", "key_moments", "vertical_crop", "subtitles",
            "background_music", "export_clips"} <= set(types)
    selector = next(node for node in plan.graph.nodes if node.type_id == "key_moments")
    assert selector.params["mode"] == "highlights"
    assert selector.params["count"] == 3
    assert next(node for node in plan.graph.nodes if node.type_id == "source").params["source"] == "talk.mp4"
    assert plan.graph.meta["requires_approval"] is True


def test_local_planner_keeps_requested_paths_empty_for_review():
    plan = WorkflowPlanner(AppConfig()).plan(
        "Make a vertical reel with my logo, intro, outro, and background music",
        mode="local",
    )

    by_type = {node.type_id: node for node in plan.graph.nodes}
    assert by_type["logo"].params["logo_path"] == ""
    assert by_type["intro_outro"].params["intro_clip"] == ""
    assert by_type["background_music"].params["track"] == ""
    assert any("logo file" in warning.lower() for warning in plan.warnings)


def test_auto_mode_uses_offline_fallback_without_key():
    plan = WorkflowPlanner(AppConfig()).plan("Trim this to under 30 seconds", mode="auto")

    assert plan.planner == "local"
    assert _types(plan) == ["source", "cut_trim", "export"]
    cut = next(node for node in plan.graph.nodes if node.type_id == "cut_trim")
    assert cut.params["max_duration"] == 30
    assert "local planner" in plan.warnings[0].lower()


def test_highlight_reel_retranscribes_after_timeline_reassembly():
    plan = WorkflowPlanner(AppConfig()).plan(
        "Make one highlight reel under 45 seconds with captions",
        mode="local",
    )

    transcripts = [node for node in plan.graph.nodes if node.type_id == "transcribe"]
    assert len(transcripts) == 2
    assembled = next(node for node in plan.graph.nodes if node.type_id == "moments_cut")
    caption_asr = transcripts[-1]
    assert any(
        edge.source == assembled.id and edge.target == caption_asr.id
        for edge in plan.graph.edges
    )


def test_ai_mode_requires_configured_key():
    with pytest.raises(WorkflowPlanningError, match="No API key"):
        WorkflowPlanner(AppConfig()).plan("Make a short", mode="ai")


def test_ai_planner_output_is_compiled_and_validated(monkeypatch):
    from core import llm

    def fake_generate(_prompt, schema, **_kwargs):
        return schema.model_validate({
            "name": "AI short",
            "summary": "A minimal short-video workflow.",
            "nodes": [
                {"id": "src", "type_id": "source", "params": {"source": "invented.mp4"}},
                {"id": "out", "type_id": "export", "params": {"quality": "High"}},
            ],
            "edges": [
                {"source": "src", "source_port": "media", "target": "out", "target_port": "media"},
            ],
            "warnings": [],
        })

    monkeypatch.setattr(llm, "generate_structured", fake_generate)
    plan = WorkflowPlanner(AppConfig(google_api_key="configured")).plan(
        "Make a clean export", source="real.mp4", mode="ai"
    )

    assert plan.planner == "llm:gemini"
    assert plan.graph.nodes[0].params["source"] == "real.mp4"
    plan.graph.validate()


@pytest.mark.parametrize("brief", ["", "   "])
def test_empty_brief_is_rejected(brief):
    with pytest.raises(WorkflowPlanningError, match="Describe"):
        WorkflowPlanner(AppConfig()).plan(brief, mode="local")
