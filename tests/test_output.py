"""Output & auto-publish: folder publisher, credentials, uploaders, scheduler."""
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from publishing.credentials import CredentialStore
from publishing.folder_publisher import publish_to_folder, render_dir_for
from publishing.scheduler import PublishScheduler
from publishing.uploaders import get_uploader, uploader_status
from publishing.uploaders.base import UploadRequest, UploadResult
from publishing.uploaders.playwright import PlaywrightUploader
from publishing.uploaders.youtube import build_request_body


# --- folder publisher ---------------------------------------------------------
def test_publish_to_folder_with_sidecars(tmp_path):
    vid = tmp_path / "out.mp4"
    vid.write_bytes(b"video")
    (tmp_path / "out_rights.json").write_text("{}")
    (tmp_path / "out_metadata.json").write_text("{}")
    renders = tmp_path / "renders"
    dest = publish_to_folder(str(vid), renders_dir=str(renders))
    assert os.path.isfile(dest)
    day_dir = os.path.dirname(dest)
    names = set(os.listdir(day_dir))
    assert {"out.mp4", "out_rights.json", "out_metadata.json"} <= names


def test_render_dir_is_dated(tmp_path):
    d = render_dir_for(str(tmp_path / "renders"))
    assert os.path.isdir(d)
    assert os.path.basename(d).count("-") == 2  # YYYY-MM-DD


# --- credentials --------------------------------------------------------------
def test_credential_store_round_trip(tmp_path):
    store = CredentialStore(str(tmp_path / "creds"))
    assert store.exists("youtube") is False
    store.save("youtube", {"token": "abc"})
    assert store.load("youtube") == {"token": "abc"}
    assert store.status(["youtube", "instagram"]) == {"youtube": True, "instagram": False}
    assert os.path.isfile(os.path.join(str(tmp_path / "creds"), ".gitignore"))


# --- uploaders ----------------------------------------------------------------
def test_folder_uploader_available_and_uploads(tmp_path):
    class Cfg:
        renders_dir = str(tmp_path / "renders")
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"x")
    up = get_uploader("folder", Cfg())
    assert up.available() is True
    res = up.upload(UploadRequest(video_path=str(vid), title="t"))
    assert res.ok and os.path.isfile(res.url)


def test_youtube_request_body_defaults_private():
    body = build_request_body(UploadRequest(video_path="x.mp4", title="Hi", tags=["a"]))
    assert body["status"]["privacyStatus"] == "private"
    assert body["snippet"]["title"] == "Hi"
    assert body["snippet"]["tags"] == ["a"]


def test_youtube_request_body_clamps_privacy():
    body = build_request_body(UploadRequest(video_path="x", privacy="garbage"))
    assert body["status"]["privacyStatus"] == "private"


def test_uploader_status_lists_platforms():
    statuses = {u["platform"]: u for u in uploader_status()}
    assert statuses["folder"]["available"] is True
    # missing deps/creds in this env -> unavailable with a reason
    assert statuses["youtube"]["available"] is False
    assert statuses["youtube"]["reason"]


def test_playwright_stub_does_not_report_success(monkeypatch):
    class FakePage:
        def goto(self, url):
            assert url == "https://www.tiktok.com/upload"

    class FakeContext:
        def new_page(self):
            return FakePage()

    class FakeBrowser:
        def new_context(self, storage_state):
            assert storage_state == {"cookies": []}
            return FakeContext()

        def close(self):
            pass

    class FakeChromium:
        def launch(self, headless):
            assert headless is True
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

    uploader = PlaywrightUploader(platform="tiktok")
    monkeypatch.setattr(uploader, "_deps", lambda: FakePlaywright)
    monkeypatch.setattr(uploader, "_storage_state", lambda: {"cookies": []})

    result = uploader.upload(UploadRequest(video_path="clip.mp4"))

    assert result.ok is False
    assert "no upload was attempted" in result.error


# --- scheduler ----------------------------------------------------------------
def _recording_factory(log):
    def factory(platform, config):
        class _U:
            def upload(self, req):
                log.append((platform, req.video_path))
                return UploadResult(ok=True, platform=platform, url="dest://" + req.video_path)
        return _U()
    return factory


def test_scheduler_runs_due_jobs(tmp_path):
    log = []
    sched = PublishScheduler(store_path=str(tmp_path / "sch.json"),
                             uploader_factory=_recording_factory(log))
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    sched.add(video_path="due.mp4", platform="folder", publish_at=past)
    sched.add(video_path="later.mp4", platform="folder", publish_at=future)
    fired = sched.run_due()
    assert [f.video_path for f in fired] == ["due.mp4"]
    assert log == [("folder", "due.mp4")]
    assert sched.get(fired[0].id).status == "published"


def test_scheduler_persists_claim_before_upload(tmp_path):
    store = tmp_path / "sch.json"
    upload_started = threading.Event()
    release_upload = threading.Event()

    def factory(platform, config):
        class _U:
            def upload(self, req):
                upload_started.set()
                assert release_upload.wait(timeout=5)
                return UploadResult(ok=True, platform=platform, url="dest://clip")
        return _U()

    sched = PublishScheduler(store_path=str(store), uploader_factory=factory)
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    item = sched.add(video_path="clip.mp4", publish_at=past)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(sched.run_due)
        assert upload_started.wait(timeout=5)
        persisted = next(row for row in json.loads(store.read_text()) if row["id"] == item.id)
        assert persisted["status"] == "publishing"
        assert persisted["claimed_at"]
        release_upload.set()
        future.result(timeout=5)


def test_scheduler_concurrent_run_due_publishes_once(tmp_path):
    calls = []
    calls_lock = threading.Lock()
    upload_started = threading.Event()
    release_upload = threading.Event()

    def factory(platform, config):
        class _U:
            def upload(self, req):
                with calls_lock:
                    calls.append(req.video_path)
                upload_started.set()
                assert release_upload.wait(timeout=5)
                return UploadResult(ok=True, platform=platform, url="dest://clip")
        return _U()

    sched = PublishScheduler(
        store_path=str(tmp_path / "sch.json"),
        uploader_factory=factory,
    )
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    item = sched.add(video_path="clip.mp4", publish_at=past)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(sched.run_due)
        assert upload_started.wait(timeout=5)
        second = pool.submit(sched.run_due)
        assert second.result(timeout=5) == []
        release_upload.set()
        assert [fired.id for fired in first.result(timeout=5)] == [item.id]

    assert calls == ["clip.mp4"]
    assert sched.get(item.id).status == "published"


def test_scheduler_recurrence_reschedules(tmp_path):
    log = []
    sched = PublishScheduler(store_path=str(tmp_path / "sch.json"),
                             uploader_factory=_recording_factory(log))
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    item = sched.add(video_path="daily.mp4", platform="folder", publish_at=past, recurrence="daily")
    sched.run_due()
    refreshed = sched.get(item.id)
    assert refreshed.status == "scheduled"          # still active
    assert refreshed.publish_at > past               # advanced ~1 day


def test_scheduler_batch_cadence(tmp_path):
    sched = PublishScheduler(store_path=str(tmp_path / "sch.json"))
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    items = sched.schedule_batch(["a.mp4", "b.mp4", "c.mp4"], platform="folder",
                                 start_at=start, interval=timedelta(days=1))
    assert len(items) == 3
    times = [i.publish_at for i in items]
    assert times == sorted(times)                    # spaced one day apart, ascending


def test_scheduler_persists_and_reloads(tmp_path):
    store = str(tmp_path / "sch.json")
    sched = PublishScheduler(store_path=store)
    item = sched.add(video_path="keep.mp4", platform="folder")
    reloaded = PublishScheduler(store_path=store)
    assert reloaded.get(item.id) is not None
    assert reloaded.get(item.id).video_path == "keep.mp4"


def test_scheduler_cancel(tmp_path):
    sched = PublishScheduler(store_path=str(tmp_path / "sch.json"))
    item = sched.add(video_path="x.mp4")
    assert sched.cancel(item.id) is True
    assert sched.get(item.id).status == "canceled"
    assert sched.cancel(item.id) is False            # already canceled
