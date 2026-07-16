from .settings import (
    LLM_KEY_FIELDS,
    AppConfig,
    load_config,
    load_llm_keys,
    save_llm_keys,
)

_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Force reload on next get_config() call. Useful in tests."""
    global _config
    _config = None


__all__ = [
    "AppConfig",
    "load_config",
    "get_config",
    "reset_config",
    "LLM_KEY_FIELDS",
    "load_llm_keys",
    "save_llm_keys",
]
