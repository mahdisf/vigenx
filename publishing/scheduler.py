"""Dependency-free background publish scheduler.

Scheduled publishes are persisted to JSON and fired by a background thread (or
driven manually via :meth:`run_due` in tests). Supports per-item recurrence and
a batch helper for the common "N videos, one per day" cadence.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

log = logging.getLogger(__name__)

RECURRENCES = ("none", "hourly", "daily", "weekly")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(iso: str) -> datetime:
    dt = datetime.fromisoformat(iso)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class ScheduledPublish:
    video_path: str
    job_id: str = ""
    platform: str = "folder"
    publish_at: str = field(default_factory=lambda: _now().isoformat())
    recurrence: str = "none"
    title: str = ""
    description: str = ""
    tags: list = field(default_factory=list)
    privacy: str = "private"
    status: str = "scheduled"  # scheduled | publishing | published | error | canceled
    claimed_at: Optional[str] = None
    last_run: Optional[str] = None
    last_error: str = ""
    result_url: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: _now().isoformat())


def _next_time(publish_at: str, recurrence: str) -> Optional[str]:
    if recurrence == "hourly":
        delta = timedelta(hours=1)
    elif recurrence == "daily":
        delta = timedelta(days=1)
    elif recurrence == "weekly":
        delta = timedelta(weeks=1)
    else:
        return None
    return (_parse(publish_at) + delta).isoformat()


class PublishScheduler:
    def __init__(
        self,
        store_path: str = "jobs/schedule.json",
        config=None,
        uploader_factory: Optional[Callable] = None,
        tick: float = 30.0,
    ) -> None:
        self.store_path = store_path
        self.config = config
        self.tick = tick
        self._uploader_factory = uploader_factory
        self._items: Dict[str, ScheduledPublish] = {}
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self.store_path):
            return
        try:
            with open(self.store_path, encoding="utf-8") as f:
                data = json.load(f)
            for item_data in data:
                item = ScheduledPublish(**item_data)
                self._items[item.id] = item
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not load schedule store: %s", exc)

    def _persist(self) -> None:
        parent = os.path.dirname(self.store_path) or "."
        if parent:
            os.makedirs(parent, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=parent,
            prefix=".schedule.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump([asdict(item) for item in self._items.values()], f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.store_path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

    def add(self, **kwargs) -> ScheduledPublish:
        item = ScheduledPublish(**kwargs)
        if item.recurrence not in RECURRENCES:
            item.recurrence = "none"
        with self._lock:
            self._items[item.id] = item
            self._persist()
        return item

    def schedule_batch(
        self,
        video_paths: List[str],
        platform: str = "folder",
        start_at: Optional[datetime] = None,
        interval: timedelta = timedelta(days=1),
        **meta,
    ) -> List[ScheduledPublish]:
        """Queue many videos spaced by ``interval``."""
        start = start_at or _now()
        created = []
        for index, path in enumerate(video_paths):
            created.append(
                self.add(
                    video_path=path,
                    platform=platform,
                    publish_at=(start + index * interval).isoformat(),
                    **meta,
                )
            )
        return created

    def list_all(self) -> List[ScheduledPublish]:
        with self._lock:
            return sorted(self._items.values(), key=lambda item: item.publish_at)

    def get(self, item_id: str) -> Optional[ScheduledPublish]:
        with self._lock:
            return self._items.get(item_id)

    def cancel(self, item_id: str) -> bool:
        with self._lock:
            item = self._items.get(item_id)
            if not item or item.status != "scheduled":
                return False
            item.status = "canceled"
            self._persist()
            return True

    def remove(self, item_id: str) -> bool:
        with self._lock:
            if item_id in self._items:
                del self._items[item_id]
                self._persist()
                return True
            return False

    def due(self, now: Optional[datetime] = None) -> List[ScheduledPublish]:
        now = now or _now()
        with self._lock:
            return [
                item
                for item in self._items.values()
                if item.status == "scheduled" and _parse(item.publish_at) <= now
            ]

    def _claim_due(self, now: datetime) -> List[ScheduledPublish]:
        """Persist ownership of due items before any uploader side effect begins."""
        with self._lock:
            claimed = [
                item
                for item in self._items.values()
                if item.status == "scheduled" and _parse(item.publish_at) <= now
            ]
            if not claimed:
                return []

            claimed_at = now.isoformat()
            for item in claimed:
                item.status = "publishing"
                item.claimed_at = claimed_at
            try:
                self._persist()
            except BaseException:
                for item in claimed:
                    item.status = "scheduled"
                    item.claimed_at = None
                raise
            return claimed

    def _uploader(self, platform: str):
        if self._uploader_factory:
            return self._uploader_factory(platform, self.config)
        from publishing.uploaders import get_uploader

        return get_uploader(platform, self.config)

    def run_due(self, now: Optional[datetime] = None) -> List[ScheduledPublish]:
        from publishing.uploaders.base import UploadRequest

        now = now or _now()
        fired: List[ScheduledPublish] = []
        for item in self._claim_due(now):
            request = UploadRequest(
                video_path=item.video_path,
                title=item.title,
                description=item.description,
                tags=list(item.tags),
                privacy=item.privacy,
            )
            try:
                result = self._uploader(item.platform).upload(request)
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    item.status, item.last_error = "error", str(exc)
                    item.last_run = now.isoformat()
                    item.claimed_at = None
                    self._persist()
                fired.append(item)
                continue

            with self._lock:
                item.last_run = now.isoformat()
                item.claimed_at = None
                if result.ok:
                    item.result_url = result.url
                    item.last_error = ""
                    next_publish_at = _next_time(item.publish_at, item.recurrence)
                    if next_publish_at:
                        item.publish_at = next_publish_at
                        item.status = "scheduled"
                    else:
                        item.status = "published"
                else:
                    item.status, item.last_error = "error", result.error
                self._persist()
            fired.append(item)
        return fired

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop():
            while not self._stop.wait(self.tick):
                try:
                    self.run_due()
                except Exception:  # noqa: BLE001
                    log.exception("Scheduler tick failed")

        self._thread = threading.Thread(target=_loop, name="vigenx-scheduler", daemon=True)
        self._thread.start()
        log.info("Publish scheduler started (tick=%ss)", self.tick)

    def stop(self) -> None:
        self._stop.set()


__all__ = ["PublishScheduler", "ScheduledPublish", "RECURRENCES"]
