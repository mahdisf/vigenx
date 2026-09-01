from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

log = logging.getLogger(__name__)

JOB_STATUSES = ("queued", "running", "awaiting_review", "approved", "rejected", "done", "error")
TERMINAL_STATUSES = {"awaiting_review", "approved", "rejected", "done", "error"}
JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


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
    manifests: list = field(default_factory=list)     # rights sidecars for graph outputs
    metadata_files: list = field(default_factory=list)  # metadata sidecars for graph outputs
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
        self._lock = threading.RLock()

    def _path(self, job_id: str) -> str:
        if not isinstance(job_id, str) or not JOB_ID_PATTERN.fullmatch(job_id):
            raise ValueError("Invalid job id")
        return os.path.join(self.jobs_dir, f"{job_id}.json")

    def _save_unlocked(self, job: Job) -> None:
        destination = self._path(job.id)
        fd, tmp_path = tempfile.mkstemp(
            dir=self.jobs_dir,
            prefix=f".{job.id}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(asdict(job), f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, destination)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

    def save(self, job: Job) -> None:
        with self._lock:
            self._save_unlocked(job)

    def _load_unlocked(self, job_id: str) -> Job:
        with open(self._path(job_id), encoding="utf-8") as f:
            data = json.load(f)
        return Job(**data)

    def load(self, job_id: str) -> Job:
        with self._lock:
            return self._load_unlocked(job_id)

    def exists(self, job_id: str) -> bool:
        with self._lock:
            try:
                path = self._path(job_id)
            except ValueError:
                return False
            return os.path.isfile(path)

    def list_all(self) -> list[Job]:
        with self._lock:
            jobs = []
            for fname in sorted(os.listdir(self.jobs_dir), reverse=True):
                if fname.endswith(".json"):
                    try:
                        jobs.append(self._load_unlocked(fname[:-5]))
                    except Exception as exc:
                        log.warning("Could not load job file %s: %s", fname, exc)
            return jobs

    def mutate(self, job_id: str, mutator: Callable[[Job], None]) -> Optional[Job]:
        """Apply a read-modify-write mutation without exposing a stale job copy."""
        with self._lock:
            path = self._path(job_id)
            if not os.path.isfile(path):
                return None
            job = self._load_unlocked(job_id)
            mutator(job)
            self._save_unlocked(job)
            return job

    def update_job(self, job_id: str, **changes: object) -> Optional[Job]:
        unknown = set(changes) - set(Job.__dataclass_fields__)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise AttributeError(f"Unknown Job field(s): {names}")

        def apply(job: Job) -> None:
            for name, value in changes.items():
                setattr(job, name, value)

        return self.mutate(job_id, apply)

    def update_node_status(self, job_id: str, node_id: str, state: dict) -> Optional[Job]:
        def apply(job: Job) -> None:
            job.node_status[node_id] = dict(state)

        return self.mutate(job_id, apply)

    def update_progress(
        self,
        job_id: str,
        message: str,
        pct: float,
        *,
        node_id: Optional[str] = None,
        node_state: Optional[dict] = None,
    ) -> Optional[Job]:
        def apply(job: Job) -> None:
            job.progress_pct = round(pct * 100, 1)
            job.log_lines.append(f"[{pct * 100:.0f}%] {message}")
            if node_id is not None and node_state is not None:
                job.node_status[node_id] = dict(node_state)

        return self.mutate(job_id, apply)
