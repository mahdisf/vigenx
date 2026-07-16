from __future__ import annotations

import logging
import threading

from config import AppConfig
from web.job_store import Job, JobStore

log = logging.getLogger(__name__)


def run_job(job: Job, cfg: AppConfig, store: JobStore) -> None:
    """Launch a job in a background thread and update its state.

    Graph jobs (``job.graph`` / ``job.template_id``) run through the ViGenX engine
    over the selected source refs; legacy jobs use the old monolithic pipelines.
    """

    def _run() -> None:
        try:
            job.status = "running"
            store.save(job)
            if job.is_graph:
                _run_graph_job(job, cfg, store)
            else:
                _run_legacy_job(job, cfg, store)
        except Exception as exc:  # noqa: BLE001
            log.exception("Job %s failed", job.id)
            job.status = "error"
            job.error_message = str(exc)
            store.save(job)

    t = threading.Thread(target=_run, name=f"job-{job.id}", daemon=True)
    t.start()


# --- graph engine path --------------------------------------------------------
def _run_graph_job(job: Job, cfg: AppConfig, store: JobStore) -> None:
    from engine.executor import GraphExecutor, NodeExecutionError
    from engine.graph import PipelineGraph
    from engine.templates import load_template

    if job.graph:
        graph = PipelineGraph.from_dict(job.graph)
    else:
        graph = load_template(job.template_id, cfg.templates_dir)
    graph.validate()

    source_nodes = [n.id for n in graph.nodes if n.type_id == "source"]
    # Each selected source ref => one run, overriding the source node's params.
    refs = job.source_refs or [None]
    total = max(1, len(refs))
    outputs: list[str] = []

    for i, ref in enumerate(refs):
        overrides = {}
        if ref and source_nodes:
            src_params = {"source": ref.get("source", ""),
                          "source_type": ref.get("source_type", "local")}
            overrides = {nid: src_params for nid in source_nodes}

        def progress_cb(node_id, message, frac, _i=i):
            overall = (_i + frac) / total
            done = message.startswith(("Done", "Export complete", "complete"))
            job.node_status[node_id] = {
                "status": "done" if done else "running",
                "message": message, "pct": round(frac * 100, 1),
            }
            store.update_progress(job.id, f"[{_i + 1}/{total}] [{node_id}] {message}", overall)

        executor = GraphExecutor(graph, cfg, progress_cb=progress_cb)
        try:
            result = executor.run(param_overrides=overrides)
        except NodeExecutionError as exc:
            job.node_status[exc.node_id] = {"status": "error", "message": str(exc.cause), "pct": 0}
            raise
        produced = result.media_paths()
        outputs.extend(produced)
        log.info("Job %s: source %d/%d produced %s", job.id, i + 1, total, produced)

    job.outputs = outputs
    job.output_path = outputs[0] if outputs else None
    job.status = "awaiting_review"
    store.save(job)
    log.info("Graph job %s completed → awaiting review (%d outputs)", job.id, len(outputs))


# --- legacy pipeline path -----------------------------------------------------
def _run_legacy_job(job: Job, cfg: AppConfig, store: JobStore) -> None:
    progress_cb = lambda msg, pct: store.update_progress(job.id, msg, pct)

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


def _get_pipeline_cls(pipeline_type: str):
    if pipeline_type == "game":
        from pipelines.game_pipeline import GameHighlightPipeline
        return GameHighlightPipeline
    if pipeline_type == "speaker":
        from pipelines.speaker_pipeline import SpeakerPipeline
        return SpeakerPipeline
    from pipelines.general_pipeline import GeneralPipeline
    return GeneralPipeline
