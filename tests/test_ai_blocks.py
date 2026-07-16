"""Tests for the AI/LLM layer, the multi-clip path, and the new web endpoints.

All LLM calls are stubbed — no network access. The block tests patch the
``llm_text``/``llm_structured`` helpers imported into each block module.
"""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import core.llm as llm
from config import AppConfig, load_llm_keys, save_llm_keys
from config.settings import apply_llm_keys
from engine.context import ExecutionContext
from engine.ports import MediaRef, Moment, Moments, Subtitles


def _subs(rows):
    return Subtitles(segments=[{"start": s, "end": e, "text": t} for s, e, t in rows])


def _ctx():
    return ExecutionContext(config=AppConfig())


# --- core.llm dispatch --------------------------------------------------------
def test_llm_text_routes_to_gemini(monkeypatch):
    import core.gemini_client as gc
    monkeypatch.setattr(gc, "generate_text",
                        lambda prompt, model_name, api_key: f"G:{model_name}")
    assert llm.generate_text("hi", provider="gemini", model="m") == "G:m"


def test_llm_text_routes_to_openai_provider(monkeypatch):
    seen = {}

    def fake_chat(provider, model, prompt, api_key, json_mode=False):
        seen.update(provider=provider, model=model)
        return "ok"

    monkeypatch.setattr(llm, "_openai_chat", fake_chat)
    out = llm.generate_text("hi", provider="groq", model=None, api_key="x")
    assert out == "ok"
    assert seen["provider"] == "groq"
    assert seen["model"] == llm.DEFAULT_MODELS["groq"]  # blank -> provider default


def test_api_key_for_maps_provider_to_config():
    cfg = AppConfig(groq_api_key="gk", nvidia_api_key="nk")
    assert llm.api_key_for(cfg, "groq") == "gk"
    assert llm.api_key_for(cfg, "nvidia") == "nk"
    assert llm.api_key_for(cfg, "gemini") == cfg.google_api_key


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        llm.normalize_provider("openai")


# --- AI blocks (stubbed LLM) --------------------------------------------------
def test_ai_extract_clamps_and_dedupes(monkeypatch):
    import engine.blocks.ai_extract as mod

    def fake_structured(ctx, block, prompt, schema):
        return SimpleNamespace(moments=[
            SimpleNamespace(start=0.0, end=4.0, score=0.9, reason="hook"),   # < min -> 8
            SimpleNamespace(start=20.0, end=200.0, score=0.8, reason="big"),  # > max -> 60
        ])

    monkeypatch.setattr(mod, "llm_structured", fake_structured)
    block = mod.AIExtractBlock({"count": 10, "min_clip": 8, "max_clip": 60})
    out = block.process(_ctx(), {"subtitles": _subs([(0, 4, "a"), (20, 30, "b")])})
    items = out["moments"].items
    assert len(items) == 2
    assert round(items[0].end - items[0].start, 1) == 8.0
    assert round(items[1].end - items[1].start, 1) == 60.0
    assert items[0].start < items[1].start  # chronological


def test_ai_extract_empty_subtitles_returns_empty():
    import engine.blocks.ai_extract as mod
    out = mod.AIExtractBlock({}).process(_ctx(), {"subtitles": Subtitles(segments=[])})
    assert out["moments"].items == []


def test_ai_text_generates_value(monkeypatch):
    import engine.blocks.ai_text as mod
    monkeypatch.setattr(mod, "llm_text", lambda ctx, block, prompt: "MY TITLE")
    block = mod.AITextBlock({"kind": "title"})
    out = block.process(_ctx(), {"subtitles": _subs([(0, 2, "hello world")])})
    assert out["text"].value == "MY TITLE"


def test_ai_subtitles_rewrites_preserving_timings(monkeypatch):
    import engine.blocks.ai_subtitles as mod

    def fake_structured(ctx, block, prompt, schema):
        return SimpleNamespace(lines=[
            SimpleNamespace(index=0, text="Hello."),
            SimpleNamespace(index=1, text="World."),
        ])

    monkeypatch.setattr(mod, "llm_structured", fake_structured)
    block = mod.AISubtitlesBlock({"mode": "clean"})
    out = block.process(_ctx(), {"subtitles": _subs([(0.0, 1.0, "helo"), (1.0, 2.0, "wrld")])})
    segs = out["subtitles"].segments
    assert [s.text for s in segs] == ["Hello.", "World."]
    assert [(s.start, s.end) for s in segs] == [(0.0, 1.0), (1.0, 2.0)]


# --- Key Moments highlights mode ---------------------------------------------
def test_key_moments_highlights_returns_varied_list():
    import engine.blocks.key_moments as mod
    rows = [(i * 3.0, i * 3.0 + 3.0, "this is an important key point") for i in range(8)]
    block = mod.KeyMomentsBlock({"mode": "highlights", "count": 2,
                                 "min_clip": 5, "max_clip": 20})
    items = block.process(None, {"subtitles": _subs(rows)})["moments"].items
    assert 1 <= len(items) <= 2
    for m in items:
        assert 5.0 <= (m.end - m.start) <= 20.0
        assert m.text
    starts = [m.start for m in items]
    assert starts == sorted(starts)  # chronological, non-overlapping


# --- RunResult multi-clip expansion ------------------------------------------
def test_media_paths_expands_clip_bundle():
    from engine.executor import RunResult
    rr = RunResult(terminal_outputs={
        "e": {"video": MediaRef(path="a.mp4", meta={"clips": ["a.mp4", "b.mp4", "c.mp4"]})}
    })
    assert rr.media_paths() == ["a.mp4", "b.mp4", "c.mp4"]


def test_media_paths_single_when_no_bundle():
    from engine.executor import RunResult
    rr = RunResult(terminal_outputs={"e": {"video": MediaRef(path="x.mp4")}})
    assert rr.media_paths() == ["x.mp4"]


# --- LLM key persistence ------------------------------------------------------
def test_llm_keys_roundtrip_and_apply(tmp_path):
    save_llm_keys(str(tmp_path), {"groq": "abc", "ignored": "x"})
    assert load_llm_keys(str(tmp_path)) == {"groq": "abc"}

    if os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY set in env (env wins over stored keys)")
    cfg = AppConfig(groq_api_key="")
    cfg.credentials_dir = str(tmp_path)
    apply_llm_keys(cfg)
    assert cfg.groq_api_key == "abc"


# --- new web endpoints --------------------------------------------------------
@pytest.fixture()
def client(tmp_path):
    from web import create_app
    app = create_app()
    app.config["CR_CONFIG"].templates_dir = str(tmp_path / "templates")
    yield app.test_client()


def test_fs_list_lists_dir(client, tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "clip.mp4").write_bytes(b"x")
    data = client.get("/api/fs/list", query_string={"path": str(tmp_path)}).get_json()
    assert any(d["name"] == "sub" for d in data["dirs"])
    assert any(f["name"] == "clip.mp4" for f in data["files"])


def test_fs_list_filters_by_ext(client, tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.txt").write_bytes(b"x")
    data = client.get("/api/fs/list",
                      query_string={"path": str(tmp_path), "exts": "mp4"}).get_json()
    names = {f["name"] for f in data["files"]}
    assert names == {"a.mp4"}


def test_fs_list_bad_path_400(client):
    r = client.get("/api/fs/list", query_string={"path": "Z:/definitely/not/here_xyz"})
    assert r.status_code == 400


def test_fonts_endpoint(client):
    data = client.get("/api/fonts").get_json()
    assert isinstance(data["fonts"], list)


def test_blocks_include_new_ai_and_clips(client):
    ids = {b["type_id"] for b in client.get("/api/blocks").get_json()["blocks"]}
    assert {"ai_text", "ai_subtitles", "export_clips"} <= ids
