from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    title: str
    description: str
    tags: list[str]
    pipeline_type: str
    duration_seconds: float
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    render_settings: dict = field(default_factory=dict)
    timestamps: list[dict] = field(default_factory=list)


def save_metadata(metadata: VideoMetadata, output_dir: str, base_name: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{base_name}_metadata.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)
    log.info("Metadata saved: %s", path)
    return path
