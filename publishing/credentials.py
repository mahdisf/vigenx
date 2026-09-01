"""Per-platform credential store for OAuth tokens and cookies.

Credentials live under a gitignored ``credentials/`` directory. Keys are never
written to TOML; this mirrors the environment-only API-key policy in
``config/settings.py``.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional

log = logging.getLogger(__name__)


class CredentialStore:
    def __init__(self, credentials_dir: str = "credentials") -> None:
        self.dir = credentials_dir
        os.makedirs(self.dir, exist_ok=True)
        self._ensure_gitignore()

    def _ensure_gitignore(self) -> None:
        gi = os.path.join(self.dir, ".gitignore")
        if not os.path.isfile(gi):
            try:
                with open(gi, "w", encoding="utf-8") as f:
                    f.write("# Never commit credentials\n*\n!.gitignore\n")
            except OSError:
                pass

    def path(self, platform: str) -> str:
        return os.path.join(self.dir, f"{platform}.json")

    def exists(self, platform: str) -> bool:
        return os.path.isfile(self.path(platform))

    def save(self, platform: str, data: Dict) -> str:
        p = self.path(platform)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        log.info("Saved credentials for %s", platform)
        return p

    def load(self, platform: str) -> Optional[Dict]:
        if not self.exists(platform):
            return None
        try:
            with open(self.path(platform), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Could not read credentials for %s: %s", platform, exc)
            return None

    def delete(self, platform: str) -> bool:
        if self.exists(platform):
            os.remove(self.path(platform))
            return True
        return False

    def status(self, platforms=("youtube", "instagram", "tiktok")) -> Dict[str, bool]:
        return {p: self.exists(p) for p in platforms}


__all__ = ["CredentialStore"]
