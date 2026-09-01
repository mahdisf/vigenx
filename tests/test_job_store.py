from concurrent.futures import ThreadPoolExecutor

import pytest

from web.job_store import Job, JobStore
from web.worker import _run_graph_job


def test_concurrent_progress_updates_do_not_lose_log_lines(tmp_path):
    store = JobStore(str(tmp_path))
    job = Job()
    store.save(job)

    updates = 40
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(
            lambda index: store.update_progress(job.id, f"update-{index}", index / updates),
            range(updates),
        ))

    saved = store.load(job.id)
    assert len(saved.log_lines) == updates
    assert {line.split(" ", 1)[1] for line in saved.log_lines} == {
        f"update-{index}" for index in range(updates)
    }


def test_graph_completion_preserves_progress_and_node_status(tmp_path, monkeypatch):
    store = JobStore(str(tmp_path))
    job = Job(graph={
        "name": "store regression",
        "nodes": [
            {"id": "source", "type_id": "source", "params": {"source": "input.mp4"}},
            {"id": "export", "type_id": "export", "params": {}},
        ],
        "edges": [{
            "source": "source",
            "source_port": "media",
            "target": "export",
            "target_port": "media",
        }],
    })
    store.save(job)

    class Result:
        @staticmethod
        def media_paths():
            return ["output.mp4"]

    class Executor:
        def __init__(self, graph, cfg, progress_cb):
            self.progress_cb = progress_cb

        def run(self, param_overrides):
            self.progress_cb("source", "Done source", 0.5)
            self.progress_cb("export", "Export complete", 1.0)
            return Result()

    monkeypatch.setattr("engine.executor.GraphExecutor", Executor)
    _run_graph_job(job, object(), store)

    saved = store.load(job.id)
    assert saved.status == "awaiting_review"
    assert saved.progress_pct == 100.0
    assert len(saved.log_lines) == 2
    assert saved.node_status["source"]["status"] == "done"
    assert saved.node_status["export"]["status"] == "done"
    assert saved.outputs == ["output.mp4"]


@pytest.mark.parametrize("job_id", ["../outside", "..\\outside", "nested/job", ""])
def test_job_ids_cannot_escape_store_directory(tmp_path, job_id):
    jobs_dir = tmp_path / "jobs"
    store = JobStore(str(jobs_dir))

    assert store.exists(job_id) is False
    with pytest.raises(ValueError, match="Invalid job id"):
        store.load(job_id)
    with pytest.raises(ValueError, match="Invalid job id"):
        store.save(Job(id=job_id))

    assert list(tmp_path.glob("outside*.json")) == []
