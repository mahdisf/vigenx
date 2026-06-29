from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from config import AppConfig

log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    output_path: str
    manifest_path: str
    metadata_path: str


ProgressCallback = Callable[[str, float], None]


class BasePipeline(abc.ABC):
    """Base class for all content-generation pipelines.

    progress_cb(message, fraction) is called at key steps with a
    human-readable status message and a 0.0–1.0 completion fraction.
    The Flask worker wires this into SSE; CLI callers get logging output.
    """

    def __init__(
        self,
        config: AppConfig,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        self.config = config
        self._progress_cb: ProgressCallback = progress_cb or self._default_progress

    def _default_progress(self, message: str, fraction: float) -> None:
        log.info("[%.0f%%] %s", fraction * 100, message)

    def _progress(self, message: str, fraction: float) -> None:
        self._progress_cb(message, fraction)

    @abc.abstractmethod
    def run(self, **kwargs) -> PipelineResult:
        ...
