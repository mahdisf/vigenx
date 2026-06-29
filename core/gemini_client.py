from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional, Type, TypeVar

log = logging.getLogger(__name__)

DEFAULT_TEXT_MODEL = "gemini-2.5-flash"
DEFAULT_VIDEO_MODEL = "gemini-2.5-flash"

T = TypeVar("T")


def _genai():
    """Lazy import so tests can mock without installing google-generativeai."""
    try:
        import google.generativeai as _g
        return _g
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai is not installed. Run: pip install google-generativeai"
        ) from exc


def configure_gemini(api_key: Optional[str] = None) -> None:
    key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "No Gemini API key found. Set GOOGLE_API_KEY environment variable."
        )
    _genai().configure(api_key=key)


def generate_text(
    prompt: str,
    model_name: str = DEFAULT_TEXT_MODEL,
    api_key: Optional[str] = None,
) -> str:
    configure_gemini(api_key)
    model = _genai().GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text or ""


def generate_structured(
    prompt: str,
    schema: Type[T],
    model_name: str = DEFAULT_TEXT_MODEL,
    api_key: Optional[str] = None,
    max_retries: int = 3,
) -> T:
    """
    Ask Gemini to return JSON matching a Pydantic schema.
    Retries up to max_retries times on parse/validation failure.
    Raises ValueError if all retries fail.
    """
    try:
        from pydantic import BaseModel, ValidationError
    except ImportError:
        raise RuntimeError(
            "pydantic is required for generate_structured. Run: pip install pydantic>=2.0"
        )

    if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
        raise TypeError("schema must be a Pydantic BaseModel subclass")

    configure_gemini(api_key)

    json_prompt = (
        f"{prompt}\n\n"
        "You MUST respond with ONLY valid JSON matching this schema. "
        "Do not include markdown code fences or any other text:\n"
        f"{json.dumps(schema.model_json_schema(), indent=2)}"
    )
    model = _genai().GenerativeModel(model_name)
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = model.generate_content(json_prompt)
            raw = (response.text or "").strip()
            # Strip optional ```json … ``` fences
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return schema.model_validate(data)  # type: ignore[return-value]
        except (json.JSONDecodeError, Exception) as e:
            log.warning(
                "generate_structured attempt %d/%d failed: %s", attempt, max_retries, e
            )
            last_error = e

    raise ValueError(
        f"Gemini did not return valid JSON after {max_retries} attempts: {last_error}"
    )


def generate_title_from_video(
    video_path: str,
    game_name: str = "",
    model_name: str = DEFAULT_VIDEO_MODEL,
    api_key: Optional[str] = None,
) -> str:
    """Analyze a gaming clip and return a viewer-reaction style title.

    The title is phrased as if other viewers are praising the play
    ("Nobody saw that coming") rather than the player self-promoting.
    Returns an empty string on failure.
    """
    g = _genai()
    configure_gemini(api_key)
    video_file = g.upload_file(path=video_path)

    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = g.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini failed to process video: {video_path}")

    game_hint = f" ({game_name} gameplay)" if game_name else ""
    prompt = (
        f"Watch this gaming clip{game_hint}. "
        "Write a short YouTube Shorts title (max 8 words) that sounds like OTHER VIEWERS "
        "praising the play — NOT the player talking about themselves. "
        "Examples: 'Nobody saw that coming', 'This clutch was INSANE', "
        "'The cleanest play I have ever seen', 'How did he even do that'. "
        "Return ONLY the title text. No quotes, no hashtags, no emojis."
    )
    model = g.GenerativeModel(model_name)
    response = model.generate_content([video_file, prompt])
    title = (response.text or "").strip()
    log.info("Gemini video title: %s", title)
    return title


def annotate_video_with_comments(
    video_path: str,
    model_name: str = DEFAULT_VIDEO_MODEL,
    api_key: Optional[str] = None,
) -> str:
    g = _genai()
    configure_gemini(api_key)
    video_file = g.upload_file(path=video_path)

    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = g.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini failed to process video: {video_path}")

    prompt = (
        "Watch this video and identify the funniest or most emotionally clear moments. "
        "For each moment, return the second, a two-word comment, and one relevant emoji. "
        "Prefer moments that would work in a short humorous edit."
    )
    model = g.GenerativeModel(model_name)
    response = model.generate_content([video_file, prompt])
    return response.text or ""
