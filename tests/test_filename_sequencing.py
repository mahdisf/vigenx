import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sources.twitch_downloader import get_next_video_id, get_next_processed_video_id


def test_empty_dir_returns_1(tmp_path):
    assert get_next_video_id(str(tmp_path), "MyGame") == 1


def test_existing_files_returns_max_plus_1(tmp_path):
    (tmp_path / "MyGame-1.mp4").touch()
    (tmp_path / "MyGame-3.mp4").touch()
    assert get_next_video_id(str(tmp_path), "MyGame") == 4


def test_non_matching_files_ignored(tmp_path):
    (tmp_path / "OtherGame-5.mp4").touch()
    (tmp_path / "MyGame-2.mp4").touch()
    (tmp_path / "MyGame-notes.txt").touch()
    assert get_next_video_id(str(tmp_path), "MyGame") == 3


def test_auto_mode_scans_processed_suffix(tmp_path):
    (tmp_path / "MyGame-1_processed.mp4").touch()
    (tmp_path / "MyGame-2_processed.mp4").touch()
    vid_id, title = get_next_processed_video_id(str(tmp_path), "MyGame", Auto=True)
    assert vid_id == 3
    assert title is None


def test_auto_mode_empty_dir_returns_1(tmp_path):
    vid_id, title = get_next_processed_video_id(str(tmp_path), "MyGame", Auto=True)
    assert vid_id == 1


def test_manual_mode_missing_file_returns_none(tmp_path):
    vid_id, title = get_next_processed_video_id(str(tmp_path), "MyGame", Auto=False)
    assert vid_id is None
    assert title is None


def test_manual_mode_returns_first_unprocessed(tmp_path):
    (tmp_path / "selected_videos.txt").write_text(
        "1,First Clip\n2,Second Clip\n3,Third Clip\n", encoding="utf-8"
    )
    (tmp_path / "MyGame-1_processed.mp4").touch()
    vid_id, title = get_next_processed_video_id(str(tmp_path), "MyGame", Auto=False)
    assert vid_id == 2
    assert title == "Second Clip"
