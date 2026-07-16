"""Resolver routing: instagram vs playlist/url vs local, with deps mocked."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sources.resolver as resolver
from sources.media_ref import MediaReference


def test_detects_instagram_and_routes(monkeypatch):
    calls = {}

    def fake_enum(source, limit=50):
        calls["source"] = source
        return [MediaReference(source_url="https://www.instagram.com/p/abc/", title="post")]

    monkeypatch.setattr("sources.instagram.enumerate_profile", fake_enum)
    refs = resolver.resolve("https://instagram.com/natgeo", "auto")
    assert calls["source"] == "https://instagram.com/natgeo"
    assert len(refs) == 1 and "instagram.com" in refs[0].source_url


def test_at_handle_routes_to_instagram(monkeypatch):
    monkeypatch.setattr("sources.instagram.enumerate_profile",
                        lambda source, limit=50: [MediaReference(source_url="x", title="t")])
    refs = resolver.resolve("@natgeo", "auto")
    assert len(refs) == 1


def test_instagram_failure_degrades_gracefully(monkeypatch):
    def boom(source, limit=50):
        raise RuntimeError("instaloader is not installed")

    monkeypatch.setattr("sources.instagram.enumerate_profile", boom)
    refs = resolver.resolve("@someone", "instagram")
    assert len(refs) == 1 and refs[0].status == "error"


def test_url_playlist_enumeration(monkeypatch):
    class FakeYDL:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def extract_info(self, url, download=False):
            return {"entries": [
                {"webpage_url": "https://yt/1", "title": "Vid 1", "duration": 10},
                {"webpage_url": "https://yt/2", "title": "Vid 2", "duration": 20},
            ]}

    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL)
    refs = resolver.resolve("https://youtube.com/playlist?list=XYZ", "url")
    assert [r.title for r in refs] == ["Vid 1", "Vid 2"]
    assert all(r.source_type == "url" for r in refs)


def test_url_single_video(monkeypatch):
    class FakeYDL:
        def __init__(self, opts): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def extract_info(self, url, download=False):
            return {"webpage_url": url, "title": "Solo", "duration": 5}

    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL)
    refs = resolver.resolve("https://youtube.com/watch?v=abc", "url")
    assert len(refs) == 1 and refs[0].title == "Solo"
