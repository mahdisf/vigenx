import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sources.media_ref import MediaReference
from sources.resolver import resolve


def test_local_single_file(tmp_path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"x")
    refs = resolve(str(f), "local")
    assert len(refs) == 1
    assert refs[0].source_type == "local"
    assert refs[0].source == os.path.abspath(str(f))


def test_local_directory(tmp_path):
    for n in ("a.mp4", "b.mov", "notes.txt", "c.mkv"):
        (tmp_path / n).write_bytes(b"x")
    refs = resolve(str(tmp_path), "local")
    titles = sorted(r.title for r in refs)
    assert titles == ["a", "b", "c"]  # txt ignored


def test_local_glob(tmp_path):
    for n in ("one.mp4", "two.mp4"):
        (tmp_path / n).write_bytes(b"x")
    refs = resolve(str(tmp_path / "*.mp4"), "local")
    assert len(refs) == 2


def test_empty_source():
    assert resolve("", "auto") == []


def test_media_reference_round_trip():
    ref = MediaReference(source_url="https://x/v", title="V", duration=12.0)
    d = ref.to_dict()
    assert d["source"] == "https://x/v" and d["source_type"] == "url"
    back = MediaReference.from_dict(d)
    assert back.source_url == "https://x/v" and back.title == "V"
