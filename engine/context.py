"""Execution context shared by every block during a graph run.

Carries the resolved :class:`~config.settings.AppConfig`, a per-run working
directory for intermediates, a progress callback, a logger, and a free-form cache
blocks may use to memoize expensive resources (e.g. loaded models).

The progress callback signature is ``(node_id, message, fraction)`` so the web SSE
layer can report per-node status. CLI/headless callers get logging by default.
"""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from config import AppConfig

log = logging.getLogger(__name__)

# (node_id, message, fraction 0..1)
ProgressCallback = Callable[[str, str, float], None]


def _default_progress(node_id: str, message: str, fraction: float) -> None:
    log.info("[%s %3.0f%%] %s", node_id, fraction * 100, message)


@dataclass
class ExecutionContext:
    config: AppConfig
    work_dir: str = ""
    progress_cb: ProgressCallback = _default_progress
    logger: logging.Logger = field(default=log)
    cache: Dict[str, Any] = field(default_factory=dict)
    preview: bool = False  # True during preview_at()/draft() runs
    current_node: str = ""  # set by the executor before each node runs

    def __post_init__(self) -> None:
        if not self.work_dir:
            self.work_dir = tempfile.mkdtemp(prefix="vigenx_")
        os.makedirs(self.work_dir, exist_ok=True)

    def node_progress(self, node_id: str, message: str, fraction: float) -> None:
        try:
            self.progress_cb(node_id, message, max(0.0, min(1.0, fraction)))
        except Exception:  # progress must never break a run
            log.debug("progress callback raised", exc_info=True)

    def progress(self, message: str, fraction: float) -> None:
        """Report sub-progress for the node currently executing.

        Blocks should use this rather than hardcoding a node id, so progress is
        attributed to the actual graph node (ids vary per graph)."""
        self.node_progress(self.current_node, message, fraction)

    def temp_path(self, name: str) -> str:
        """Absolute path for an intermediate file inside the work dir."""
        return os.path.join(self.work_dir, name)

    def subdir(self, name: str) -> str:
        path = os.path.join(self.work_dir, name)
        os.makedirs(path, exist_ok=True)
        return path


__all__ = ["ExecutionContext", "ProgressCallback"]
