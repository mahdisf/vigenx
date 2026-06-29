import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.manifest import build_default_manifest, save_manifest


def test_save_manifest_creates_file(tmp_path):
    manifest = build_default_manifest(
        output_video_path=str(tmp_path / "video.mp4"),
        source_url="https://example.com/video",
        ai_tools=["Whisper small"],
        transformation_notes="test",
    )
    path = save_manifest(manifest, str(tmp_path))
    assert os.path.isfile(path)
    assert path.endswith("_rights.json")


def test_manifest_json_is_valid(tmp_path):
    manifest = build_default_manifest(
        output_video_path=str(tmp_path / "video.mp4"),
        source_url="https://example.com/video",
        ai_tools=["Whisper small", "pyttsx3"],
        transformation_notes="silence trimming, subtitles",
        music_license="royalty-free",
    )
    path = save_manifest(manifest, str(tmp_path))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "generated_at" in data
    assert data["source_url"] == "https://example.com/video"
    assert "Whisper small" in data["ai_tools_used"]
    assert data["music_license"] == "royalty-free"


def test_policy_checklist_defaults_all_false(tmp_path):
    manifest = build_default_manifest(
        output_video_path=str(tmp_path / "video.mp4"),
        ai_tools=[],
        transformation_notes="",
    )
    path = save_manifest(manifest, str(tmp_path))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    checklist = data["policy_checklist"]
    assert all(v is False for v in checklist.values())
    assert "human_reviewed" in checklist
