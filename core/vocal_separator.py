from __future__ import annotations

import logging
import os
import shutil
import subprocess

log = logging.getLogger(__name__)


def separate_vocals_with_demucs(input_audio_path: str, output_dir: str) -> dict[str, str]:
    """
    Separate vocals from audio using Demucs.

    Returns a dict with keys 'vocals' and 'no_vocals' pointing to the output wav files,
    or a dict with key 'error' describing what went wrong.
    """
    if not shutil.which("demucs"):
        return {
            "error": (
                "Demucs is not installed or not on PATH. "
                "Run: pip install demucs"
            )
        }

    model_name = "mdx_extra_q"
    log.info("Running Demucs on %s with model %s …", input_audio_path, model_name)

    command = [
        "demucs", "--two-stems", "vocals", "-n", model_name, "-o", output_dir,
        input_audio_path,
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        log.debug("Demucs stdout: %s", result.stdout)

        vocals_path: str | None = None
        no_vocals_path: str | None = None

        for root, _dirs, files in os.walk(output_dir):
            if "vocals.wav" in files:
                vocals_path = os.path.join(root, "vocals.wav")
            if "no_vocals.wav" in files:
                no_vocals_path = os.path.join(root, "no_vocals.wav")
            if vocals_path and no_vocals_path:
                break

        if vocals_path and no_vocals_path:
            log.info("Demucs separation complete — vocals: %s, no_vocals: %s", vocals_path, no_vocals_path)
            return {"vocals": vocals_path, "no_vocals": no_vocals_path}

        return {
            "error": (
                f"Demucs ran but output files were not found inside {output_dir}"
            )
        }

    except subprocess.CalledProcessError as e:
        log.error("Demucs failed: %s", e.stderr)
        return {"error": e.stderr}
