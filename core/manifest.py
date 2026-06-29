from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class RightsManifest:
    generated_at: str
    output_video_path: str
    source_url: Optional[str]
    source_title: Optional[str]
    source_owner: Optional[str]
    permission_or_license: str
    music_license: Optional[str]
    ai_tools_used: list[str]
    transformation_notes: str
    policy_checklist: dict[str, bool] = field(default_factory=lambda: {
        "source_rights_verified": False,
        "music_rights_verified": False,
        "original_commentary_added": False,
        "synthetic_content_disclosed": False,
        "human_reviewed": False,
    })


def build_default_manifest(
    output_video_path: str,
    source_url: Optional[str] = None,
    source_title: Optional[str] = None,
    ai_tools: Optional[list[str]] = None,
    transformation_notes: str = "",
    permission: str = "unverified — review before upload",
    music_license: Optional[str] = None,
    source_owner: Optional[str] = None,
) -> RightsManifest:
    return RightsManifest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        output_video_path=output_video_path,
        source_url=source_url,
        source_title=source_title,
        source_owner=source_owner,
        permission_or_license=permission,
        music_license=music_license,
        ai_tools_used=ai_tools or [],
        transformation_notes=transformation_notes,
    )


def save_manifest(manifest: RightsManifest, output_dir: str) -> str:
    base = os.path.splitext(os.path.basename(manifest.output_video_path))[0]
    path = os.path.join(output_dir, f"{base}_rights.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(manifest), f, indent=2, ensure_ascii=False)
    log.info("Rights manifest saved: %s", path)
    return path
