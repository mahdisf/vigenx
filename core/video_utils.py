"""Video composition helpers: color filters, logo overlay, intro/outro concatenation."""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Color filters
# ---------------------------------------------------------------------------

def apply_color_filter(clip, brightness: float = 1.0, contrast: float = 1.0, saturation: float = 1.0):
    """Apply brightness, contrast, and saturation adjustments to a MoviePy clip.

    All parameters default to 1.0 (no change). Values above 1.0 increase the
    effect; below 1.0 reduce it.
    """
    if brightness != 1.0:
        from moviepy.video.fx.all import colorx  # type: ignore[import]
        clip = colorx(clip, brightness)

    if contrast != 1.0 or saturation != 1.0:
        try:
            import numpy as np
            from PIL import Image, ImageEnhance

            def _filter(frame):
                img = Image.fromarray(frame)
                if contrast != 1.0:
                    img = ImageEnhance.Contrast(img).enhance(contrast)
                if saturation != 1.0:
                    img = ImageEnhance.Color(img).enhance(saturation)
                return np.array(img)

            clip = clip.fl_image(_filter)
        except Exception as exc:
            log.warning("Color filter failed (PIL unavailable?): %s", exc)

    return clip


# ---------------------------------------------------------------------------
# Logo overlay
# ---------------------------------------------------------------------------

def add_logo_overlay(
    clip,
    logo_path: str,
    position: str = "top-right",
    opacity: float = 0.85,
    scale: float = 0.10,
):
    """Composite a PNG logo onto *clip*.

    *scale* is a fraction of the clip's width. *position* is one of:
    ``top-left``, ``top-right``, ``bottom-left``, ``bottom-right``.
    Returns the original clip unchanged if *logo_path* is empty or missing.
    """
    if not logo_path or not os.path.isfile(logo_path):
        return clip

    try:
        import numpy as np
        from PIL import Image
        from moviepy.editor import CompositeVideoClip, ImageClip  # type: ignore[import]

        logo_w = max(1, int(clip.w * scale))
        img = Image.open(logo_path).convert("RGBA")
        orig_w, orig_h = img.size
        logo_h = max(1, int(logo_w * orig_h / orig_w))
        img = img.resize((logo_w, logo_h), Image.LANCZOS)

        arr = np.array(img, dtype=float)
        arr[:, :, 3] = (arr[:, :, 3] * opacity).clip(0, 255)
        arr = arr.astype("uint8")

        logo_clip = ImageClip(arr, ismask=False).set_duration(clip.duration)

        margin = 20
        positions: dict[str, tuple[int, int]] = {
            "top-left": (margin, margin),
            "top-right": (clip.w - logo_w - margin, margin),
            "bottom-left": (margin, clip.h - logo_h - margin),
            "bottom-right": (clip.w - logo_w - margin, clip.h - logo_h - margin),
        }
        pos = positions.get(position, (margin, margin))
        logo_clip = logo_clip.set_position(pos)

        return CompositeVideoClip([clip, logo_clip])
    except Exception as exc:
        log.warning("Logo overlay failed: %s", exc)
        return clip


# ---------------------------------------------------------------------------
# Intro / outro concatenation
# ---------------------------------------------------------------------------

def prepend_append_clips(main_clip, intro_path: str = "", outro_path: str = ""):
    """Return a new clip with optional intro and outro concatenated around *main_clip*.

    Intro/outro clips are resized to match *main_clip*'s dimensions.
    Returns *main_clip* unchanged if both paths are empty or missing.
    """
    if not intro_path and not outro_path:
        return main_clip

    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips  # type: ignore[import]

        parts = []

        if intro_path and os.path.isfile(intro_path):
            intro = VideoFileClip(intro_path).resize(main_clip.size)
            parts.append(intro)
            log.info("Prepending intro: %s", intro_path)
        elif intro_path:
            log.warning("Intro clip not found, skipping: %s", intro_path)

        parts.append(main_clip)

        if outro_path and os.path.isfile(outro_path):
            outro = VideoFileClip(outro_path).resize(main_clip.size)
            parts.append(outro)
            log.info("Appending outro: %s", outro_path)
        elif outro_path:
            log.warning("Outro clip not found, skipping: %s", outro_path)

        if len(parts) == 1:
            return main_clip

        return concatenate_videoclips(parts, method="compose")
    except Exception as exc:
        log.warning("Intro/outro concatenation failed: %s", exc)
        return main_clip
