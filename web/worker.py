from __future__ import annotations

import logging
import threading

from config import AppConfig
from web.job_store import Job, JobStore

log = logging.getLogger(__name__)


def run_job(job: Job, cfg: AppConfig, store: JobStore) -> None:
    """Launch pipeline in a background thread and update job state."""

    def _run() -> None:
        try:
            progress_cb = lambda msg, pct: store.update_progress(job.id, msg, pct)
            job.status = "running"
            store.save(job)

            pipeline_cls = _get_pipeline_cls(job.pipeline_type)
            pipeline = pipeline_cls(config=cfg, progress_cb=progress_cb)
            result = pipeline.run(
                source=job.source,
                source_type=job.source_type,
                **job.options,
            )

            job.output_path = result.output_path
            job.manifest_path = result.manifest_path
            job.metadata_path = result.metadata_path
            job.status = "awaiting_review"
            store.save(job)
            log.info("Job %s completed → awaiting review", job.id)

        except Exception as exc:
            log.exception("Job %s failed", job.id)
            job.status = "error"
            job.error_message = str(exc)
            store.save(job)

    t = threading.Thread(target=_run, name=f"job-{job.id}", daemon=True)
    t.start()


def _get_pipeline_cls(pipeline_type: str):
    if pipeline_type == "game":
        from pipelines.game_pipeline import GameHighlightPipeline
        return GameHighlightPipeline
    if pipeline_type == "speaker":
        from pipelines.speaker_pipeline import SpeakerPipeline
        return SpeakerPipeline
    from pipelines.general_pipeline import GeneralPipeline
    return GeneralPipeline
