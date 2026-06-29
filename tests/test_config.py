import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import reset_config
from config.settings import AppConfig, load_config


def test_defaults_are_applied():
    cfg = AppConfig()
    assert cfg.input_dir == "downloads"
    assert cfg.output_dir == "output"
    assert cfg.max_duration == 59
    assert cfg.whisper_model == "small"
    assert cfg.tts_engine == "pyttsx3"


def test_missing_toml_uses_defaults(tmp_path):
    cfg = load_config(str(tmp_path / "nonexistent.toml"))
    assert cfg.max_duration == 59


def test_toml_overrides_defaults(tmp_path):
    toml = tmp_path / "test_config.toml"
    toml.write_text('max_duration = 30\ngame_name = "Fortnite"\n', encoding="utf-8")
    cfg = load_config(str(toml))
    assert cfg.max_duration == 30
    assert cfg.game_name == "Fortnite"


def test_env_vars_populate_api_keys(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-123")
    cfg = AppConfig()
    assert cfg.google_api_key == "test-key-123"


def test_get_config_singleton():
    from config import get_config, reset_config
    reset_config()
    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2
    reset_config()
