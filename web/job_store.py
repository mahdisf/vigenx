from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)

JOB_STATUSES = ("queued", "running", "awaiting_review", "approved", "rejected", "done", "error")
TERMINAL_STATUSES = {"awaiting_review", "approved", "rejected", "done", "error"}


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pipeline_type: str = "general"
    source_type: str = "local"
    source: str = ""
    options: dict = field(default_factory=dict)
    # --- graph engine (ViGenX) ---
    graph: Optional[dict] = None              # serialized PipelineGraph, if a graph job
    template_id: Optional[str] = None         # template to load when graph is omitted
    source_refs: list = field(default_factory=list)  # MediaReference dicts for batch runs
    node_status: dict = field(default_factory=dict)  # node_id -> {status, message, pct}
    outputs: list = field(default_factory=list)       # produced output paths (batch)
    # --- status ---
    status: str = "queued"
    progress_pct: float = 0.0
    log_lines: list[str] = field(default_factory=list)
    output_path: Optional[str] = None
    manifest_path: Optional[str] = None
    metadata_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def is_graph(self) -> bool:
        return bool(self.graph or self.template_id)


class JobStore:
    def __init__(self, jobs_dir: str = "jobs") -> None:
        self.jobs_dir = jobs_dir
        os.makedirs(jobs_dir, exist_ok=True)

    def _path(self, job_id: str) -> str:
        return os.path.join(self.jobs_dir, f"{job_id}.json")

    def save(self, job: Job) -> None:
        with open(self._path(job.id), "w", encoding="utf-8") as f:
            json.dump(asdict(job), f, indent=2, ensure_ascii=False)

    def load(self, job_id: str) -> Job:
        with open(self._path(job_id), encoding="utf-8") as f:
            data = json.load(f)
        return Job(**data)

    def exists(self, job_id: str) -> bool:
        return os.path.isfile(self._path(job_id))

    def list_all(self) -> list[Job]:
        jobs = []
        for fname in sorted(os.listdir(self.jobs_dir), reverse=True):
            if fname.endswith(".json"):
                try:
                    jobs.append(self.load(fname[:-5]))
                except Exception as exc:
                    log.warning("Could not load job file %s: %s", fname, exc)
        return jobs

    def update_progress(self, job_id: str, message: str, pct: float) -> None:
        if not self.exists(job_id):
            return
        job = self.load(job_id)
        job.progress_pct = round(pct * 100, 1)
        job.log_lines.append(f"[{pct * 100:.0f}%] {message}")
        self.save(job)
