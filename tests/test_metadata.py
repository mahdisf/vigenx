import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.metadata import VideoMetadata, save_metadata


def test_save_metadata_creates_file(tmp_path):
    meta = VideoMetadata(
        title="Test Video",
        description="A test description",
        tags=["test", "video"],
        pipeline_type="general",
        duration_seconds=42.5,
    )
    path = save_metadata(meta, str(tmp_path), "test_video")
    assert os.path.isfile(path)
    assert path.endswith("_metadata.json")


def test_metadata_roundtrip(tmp_path):
    meta = VideoMetadata(
        title="Gaming Highlight",
        description="Best clip ever",
        tags=["gaming", "highlight"],
        pipeline_type="game",
        duration_seconds=59.0,
        source_url="https://twitch.tv/clip/abc",
        render_settings={"codec": "libx264", "fps": 30, "crf": 18},
    )
    path = save_metadata(meta, str(tmp_path), "gaming_highlight")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["title"] == "Gaming Highlight"
    assert data["pipeline_type"] == "game"
    assert data["duration_seconds"] == 59.0
    assert data["render_settings"]["codec"] == "libx264"
    assert "gaming" in data["tags"]
