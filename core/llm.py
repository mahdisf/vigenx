"""Provider-agnostic LLM client used by the AI blocks.

Supports three providers, selectable per block:
  * ``gemini`` — Google Generative AI (delegates to :mod:`core.gemini_client`).
  * ``groq``   — Groq's OpenAI-compatible Chat Completions API.
  * ``nvidia`` — NVIDIA NIM's OpenAI-compatible Chat Completions API.

Each AI block exposes a ``provider`` choice and a free-text ``model`` field; the
API key for the chosen provider is resolved from :class:`~config.AppConfig`
(entered in the Settings page or via environment variables).

The two entry points mirror :mod:`core.gemini_client`:
  * :func:`generate_text` — plain text completion.
  * :func:`generate_structured` — JSON matching a Pydantic schema, with retries.
"""
from __future__ import annotations

import json
import logging
from typing import Optional, Type, TypeVar

log = logging.getLogger(__name__)

PROVIDERS = ("gemini", "groq", "nvidia")

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "nvidia": "meta/llama-3.3-70b-instruct",
}

# OpenAI-compatible base URLs for the non-Gemini providers.
_OPENAI_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
}

T = TypeVar("T")


def normalize_provider(provider: Optional[str]) -> str:
    p = (provider or "gemini").strip().lower()
    if p not in PROVIDERS:
        raise ValueError(f"Unknown LLM provider {provider!r}; choose one of {PROVIDERS}")
    return p


def default_model(provider: str) -> str:
    return DEFAULT_MODELS.get(normalize_provider(provider), "")


def api_key_for(config, provider: str) -> str:
    """Resolve the API key for ``provider`` from an :class:`AppConfig`."""
    attr = {
        "gemini": "google_api_key",
        "groq": "groq_api_key",
        "nvidia": "nvidia_api_key",
    }[normalize_provider(provider)]
    return getattr(config, attr, "") or ""


# --- OpenAI-compatible (Groq / NVIDIA) ---------------------------------------
def _openai_client(provider: str, api_key: Optional[str]):
    if not api_key:
        raise RuntimeError(
            f"No API key configured for {provider!r}. Add it in Settings "
            f"or set the {provider.upper()}_API_KEY environment variable."
        )
    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "The 'openai' package is required for Groq/NVIDIA providers. "
            "Run: pip install openai"
        ) from exc
    return OpenAI(base_url=_OPENAI_BASE_URLS[provider], api_key=api_key)


def _openai_chat(provider, model, prompt, api_key, *, json_mode=False) -> str:
    client = _openai_client(provider, api_key)
    kwargs = {
        "model": model or default_model(provider),
        "messages": [{"role": "user", "content": prompt}],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "").strip()


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


# --- public API --------------------------------------------------------------
def generate_text(
    prompt: str,
    *,
    provider: str = "gemini",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Return a plain-text completion from the selected provider."""
    provider = normalize_provider(provider)
    model = model or default_model(provider)
    if provider == "gemini":
        from core.gemini_client import generate_text as _gemini_text

        return _gemini_text(prompt, model_name=model, api_key=api_key)
    return _openai_chat(provider, model, prompt, api_key)


def generate_structured(
    prompt: str,
    schema: Type[T],
    *,
    provider: str = "gemini",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    max_retries: int = 3,
) -> T:
    """Return an instance of the Pydantic ``schema`` from the selected provider.

    For Gemini this delegates to :func:`core.gemini_client.generate_structured`.
    For Groq/NVIDIA it asks for JSON (native JSON mode) and validates with retries.
    """
    provider = normalize_provider(provider)
    model = model or default_model(provider)

    if provider == "gemini":
        from core.gemini_client import generate_structured as _gemini_structured

        return _gemini_structured(
            prompt, schema, model_name=model, api_key=api_key, max_retries=max_retries
        )

    try:
        from pydantic import BaseModel
    except ImportError as exc:  # pragma: no cover - pydantic is a project dep
        raise RuntimeError(
            "pydantic is required for generate_structured. Run: pip install pydantic>=2.0"
        ) from exc
    if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
        raise TypeError("schema must be a Pydantic BaseModel subclass")

    json_prompt = (
        f"{prompt}\n\n"
        "You MUST respond with ONLY valid JSON matching this schema. "
        "Do not include markdown code fences or any other text:\n"
        f"{json.dumps(schema.model_json_schema(), indent=2)}"
    )

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            raw = _openai_chat(provider, model, json_prompt, api_key, json_mode=True)
            data = json.loads(_strip_fences(raw))
            return schema.model_validate(data)  # type: ignore[return-value]
        except Exception as exc:  # noqa: BLE001 - retried below
            log.warning(
                "generate_structured (%s) attempt %d/%d failed: %s",
                provider, attempt, max_retries, exc,
            )
            last_error = exc

    raise ValueError(
        f"{provider} did not return valid JSON after {max_retries} attempts: {last_error}"
    )


__all__ = [
    "PROVIDERS",
    "DEFAULT_MODELS",
    "normalize_provider",
    "default_model",
    "api_key_for",
    "generate_text",
    "generate_structured",
]
