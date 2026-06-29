import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sources.twitch_downloader import is_video_downloaded, log_downloaded_video


def test_missing_history_file_returns_false(tmp_path):
    assert not is_video_downloaded("abc123", str(tmp_path / "history.txt"))


def test_logged_id_is_found(tmp_path):
    hf = str(tmp_path / "history.txt")
    log_downloaded_video("abc123", hf)
    assert is_video_downloaded("abc123", hf)


def test_unlisted_id_not_found(tmp_path):
    hf = str(tmp_path / "history.txt")
    log_downloaded_video("abc123", hf)
    assert not is_video_downloaded("xyz999", hf)


def test_duplicate_log_does_not_break_lookup(tmp_path):
    hf = str(tmp_path / "history.txt")
    log_downloaded_video("abc123", hf)
    log_downloaded_video("abc123", hf)
    assert is_video_downloaded("abc123", hf)
    # Count lines — should have 2 (duplicates written), but lookup still works
    lines = open(hf).read().strip().splitlines()
    assert len(lines) == 2
