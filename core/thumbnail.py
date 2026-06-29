"""Automated cover / thumbnail generation for pipeline output videos."""
from __future__ import annotations

import logging
import os
import subprocess

log = logging.getLogger(__name__)


def generate_thumbnail(
    video_path: str,
    output_path: str,
    timestamp: float = 5.0,
    title: str = "",
    font_path: str = "",
    text_color: str = "white",
    stroke_color: str = "#FD3C9D",
) -> str:
    """Extract a frame at *timestamp* seconds and optionally overlay title text.

    Returns *output_path* on success, or an empty string on failure.
    """
    if not os.path.isfile(video_path):
        log.warning("Thumbnail: source video not found: %s", video_path)
        return ""

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except Exception as exc:
        log.error("Thumbnail frame extraction failed: %s", exc)
        return ""

    if not os.path.isfile(output_path):
        log.error("Thumbnail: ffmpeg produced no output at %s", output_path)
        return ""

    if title:
        _add_title_bar(output_path, title, font_path, text_color, stroke_color)

    log.info("Thumbnail saved: %s", output_path)
    return output_path


def _add_title_bar(
    image_path: str,
    title: str,
    font_path: str,
    text_color: str,
    stroke_color: str,
) -> None:
    """Overlay a semi-transparent bottom bar with the title text."""
    try:
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(image_path).convert("RGBA")
        w, h = img.size
        bar_h = max(60, h // 8)

        bar = Image.new("RGBA", (w, bar_h), (0, 0, 0, 170))
        img.paste(bar, (0, h - bar_h), bar)

        draw = ImageDraw.Draw(img)
        font_size = max(28, bar_h // 2)
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont
        if font_path and os.path.isfile(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception:
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), title, font=font)
        tx = max(0, (w - (bbox[2] - bbox[0])) // 2)
        ty = h - bar_h + (bar_h - (bbox[3] - bbox[1])) // 2

        # Shadow
        draw.text((tx + 2, ty + 2), title, font=font, fill="#000000")
        # Stroke
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.text((tx + dx, ty + dy), title, font=font, fill=stroke_color)
        # Main text
        draw.text((tx, ty), title, font=font, fill=text_color)

        img.convert("RGB").save(image_path, quality=95)
    except Exception as exc:
        log.warning("Thumbnail title overlay failed: %s", exc)


def thumbnail_path_for(video_path: str) -> str:
    """Return the conventional thumbnail path next to a video file."""
    base, _ = os.path.splitext(video_path)
    return base + "_thumb.jpg"
