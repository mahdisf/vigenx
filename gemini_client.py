import os
import time
from typing import Optional

import google.generativeai as genai


DEFAULT_TEXT_MODEL = "gemini-2.5-flash"
DEFAULT_VIDEO_MODEL = "gemini-2.5-flash"


def configure_gemini(api_key: Optional[str] = None) -> None:
    """Configure Gemini from an explicit key or GOOGLE_API_KEY."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")
    genai.configure(api_key=key)


def generate_text(prompt: str, model_name: str = DEFAULT_TEXT_MODEL, api_key: Optional[str] = None) -> str:
    """Generate text for titles, commentary, descriptions, or prompts."""
    configure_gemini(api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text or ""


def annotate_video_with_comments(
    video_path: str,
    model_name: str = DEFAULT_VIDEO_MODEL,
    api_key: Optional[str] = None,
) -> str:
    """
    Ask Gemini to identify notable moments and return timestamped short comments.

    The caller should parse the returned text into structured data if strict JSON is
    needed. Keeping this as a thin wrapper makes model changes easier.
    """
    configure_gemini(api_key)
    video_file = genai.upload_file(path=video_path)

    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini failed to process video: {video_path}")

    prompt = (
        "Watch this video and identify the funniest or most emotionally clear moments. "
        "For each moment, return the second, a two-word comment, and one relevant emoji. "
        "Prefer moments that would work in a short humorous edit."
    )
    model = genai.GenerativeModel(model_name)
    response = model.generate_content([video_file, prompt])
    return response.text or ""
