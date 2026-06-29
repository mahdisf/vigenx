from __future__ import annotations

import logging
import srt
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class SubtitleSegment:
    start: float
    end: float
    text: str
    confidence: float = 1.0


def transcribe(
    audio_video_path: str,
    model_size: str = "small",
    language: Optional[str] = None,
    word_timestamps: bool = False,
) -> list[SubtitleSegment]:
    """
    Transcribe audio/video with Whisper and return segments.
    Loads the model fresh each call; callers that process many files should
    cache the model and call whisper.transcribe() directly.
    """
    import whisper  # type: ignore[import]

    log.info("Loading Whisper model: %s", model_size)
    model = whisper.load_model(model_size)
    log.info("Transcribing: %s", audio_video_path)
    result = model.transcribe(
        audio_video_path,
        language=language,
        word_timestamps=word_timestamps,
    )
    segments = [
        SubtitleSegment(
            start=seg["start"],
            end=seg["end"],
            text=seg["text"].strip(),
            confidence=seg.get("avg_logprob", 1.0),
        )
        for seg in result["segments"]
    ]
    log.info("Transcription complete — %d segments", len(segments))
    return segments


def write_srt(segments: list[SubtitleSegment], srt_path: str) -> None:
    items = [
        srt.Subtitle(
            index=i,
            start=timedelta(seconds=seg.start),
            end=timedelta(seconds=seg.end),
            content=seg.text,
        )
        for i, seg in enumerate(segments, 1)
    ]
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(items))
    log.info("SRT saved: %s", srt_path)
