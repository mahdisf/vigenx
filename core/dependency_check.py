from __future__ import annotations

import importlib
import logging
import shutil

log = logging.getLogger(__name__)

REQUIRED_BINS = ["ffmpeg", "ffprobe"]
OPTIONAL_BINS: dict[str, str] = {
    "demucs": "pip install demucs",
    "magick": "Install ImageMagick from https://imagemagick.org",
}
REQUIRED_PACKAGES = ["whisper", "cv2", "moviepy", "yt_dlp"]
OPTIONAL_PACKAGES: dict[str, str] = {
    "mediapipe": "pip install mediapipe==0.10.14",
    "ultralytics": "pip install ultralytics",
    "google.generativeai": "pip install google-generativeai",
    "pydantic": "pip install pydantic>=2.0",
    "flask": "pip install flask",
}


def check_dependencies(raise_on_missing: bool = False) -> dict[str, bool]:
    results: dict[str, bool] = {}
    missing_required: list[str] = []

    for bin_ in REQUIRED_BINS:
        ok = shutil.which(bin_) is not None
        results[bin_] = ok
        if not ok:
            missing_required.append(bin_)
            log.error("Required binary missing: %s. Install FFmpeg and ensure it is on PATH.", bin_)

    for bin_, hint in OPTIONAL_BINS.items():
        ok = shutil.which(bin_) is not None
        results[bin_] = ok
        if not ok:
            log.warning("Optional binary missing: %s — %s", bin_, hint)

    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            results[pkg] = True
        except ImportError:
            results[pkg] = False
            missing_required.append(pkg)
            log.error("Required package not importable: %s. Run: pip install -r requirements.txt", pkg)

    for pkg, hint in OPTIONAL_PACKAGES.items():
        try:
            importlib.import_module(pkg)
            results[pkg] = True
        except ImportError:
            results[pkg] = False
            log.warning("Optional package not installed: %s — %s", pkg, hint)

    if raise_on_missing and missing_required:
        raise RuntimeError(f"Missing required dependencies: {missing_required}")

    return results
