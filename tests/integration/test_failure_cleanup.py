from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from openmedia.coordinator import MediaWorkflow, RequestRegistry
from openmedia.models import RequestState
from openmedia.workers import WorkerSupervisor, WorkerTimeout, sweep_work_directories


@pytest.mark.parametrize("notification_fails", [False, True])
async def test_runtime_failure_is_notified_after_capacity_release(notification_fails):
    from unittest.mock import AsyncMock
    from openmedia.workers import WorkerRemoteError
    notices = []
    registry = RequestRegistry()
    async def notify(request, result):
        assert registry.active_work_count == 0
        notices.append(result)
        if notification_fails:
            raise RuntimeError("offline")
    workflow = MediaWorkflow(registry, inspect=AsyncMock(side_effect=WorkerRemoteError("too_large", "inspection")),
        publish_preview=AsyncMock(), download=AsyncMock(), deliver=AsyncMock(), status=AsyncMock(), notify_failure=notify, max_file_bytes=50_000_000)
    with pytest.raises(WorkerRemoteError):
        await workflow.submit(user_id=1, chat_id=1, text="https://youtu.be/abcDEF12345", chat_type="private")
    assert len(notices) == 1
    assert notices[0].error_category == "too_large"
    assert notices[0].failed_stage == "checking"


async def test_total_inspection_deadline_includes_status_send():
    import asyncio
    from unittest.mock import AsyncMock
    registry = RequestRegistry()
    async def slow(*args):
        await asyncio.sleep(1)
    workflow = MediaWorkflow(registry, inspect=AsyncMock(), publish_preview=AsyncMock(),
        download=AsyncMock(), deliver=AsyncMock(), status=slow, inspection_seconds=0.03, reap_reserve=0, max_file_bytes=50_000_000)
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(workflow.submit(user_id=1, chat_id=1, text="https://youtu.be/abcDEF12345", chat_type="private"), 0.2)
    assert registry.active_work_count == 0


async def test_total_processing_deadline_marks_interrupted_upload_unknown(tmp_path):
    import asyncio
    from unittest.mock import AsyncMock
    from openmedia.models import FormatOption, MediaMetadata
    from openmedia.sources import DownloadResult
    registry = RequestRegistry(processing_seconds=0.04)
    request = registry.new_request(user_id=1, chat_id=1, source_url="https://youtu.be/abcDEF12345", platform="youtube", media_id="abcDEF12345")
    await registry.admit(request)
    option = FormatOption(0, "fixture", "18", "video", "mp4", "video/mp4", includes_audio=True)
    await registry.publish_preview(request.request_id, metadata=MediaMetadata("youtube", request.source_url, request.media_id), options=(option,), preview_message_id=1)
    await registry.claim_selection(request.request_id, user_id=1, chat_id=1, preview_message_id=1, option_id=0)
    path = tmp_path / "video.mp4"; path.write_bytes(b"fixture")
    async def upload(*args):
        await asyncio.sleep(1)
    notify = AsyncMock()
    workflow = MediaWorkflow(registry, inspect=AsyncMock(), publish_preview=AsyncMock(), status=AsyncMock(),
        download=AsyncMock(return_value=DownloadResult(path, 7, request.media_id, "18", "video", "mp4", "video/mp4")),
        deliver=upload, notify_failure=notify, reap_reserve=0, max_file_bytes=50_000_000)
    result = await asyncio.wait_for(workflow.process_claimed(request, option), 0.2)
    assert result.status == "unknown"
    assert result.notification_sent
    assert "Check this chat" in result.next_step
    assert registry.active_work_count == 0


async def test_successful_leader_cannot_leave_a_writing_descendant(tmp_path):
    import asyncio
    marker = tmp_path / "orphan-write"
    code = "import subprocess,sys,json; subprocess.Popen([sys.executable,'-c',\"import sys,time,pathlib; time.sleep(.2); pathlib.Path(sys.argv[1]).touch()\",sys.argv[1]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(json.dumps({'event':'result','value':True}),flush=True)"
    supervisor = WorkerSupervisor([sys.executable, "-c", code, str(marker)], termination_grace=0.05)
    assert await supervisor.run("inspect", {}, timeout=1) is True
    await asyncio.sleep(0.3)
    assert not marker.exists()


async def test_exited_leader_with_pipe_holding_descendant_returns_and_is_reaped(tmp_path):
    """A descendant that inherits stdout keeps the pipe open after the leader exits."""
    import asyncio
    pid_file = tmp_path / "descendant.pid"
    code = ("import subprocess,sys,json,pathlib;"
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']);"
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid));"
        "print(json.dumps({'event':'result','value':True}),flush=True)")
    supervisor = WorkerSupervisor([sys.executable, "-c", code, str(pid_file)], termination_grace=0.2)
    assert await asyncio.wait_for(supervisor.run("inspect", {}, timeout=30), 5) is True
    descendant = int(pid_file.read_text())
    for _ in range(100):
        try:
            os.kill(descendant, 0)
        except ProcessLookupError:
            break
        await asyncio.sleep(0.02)
    else:
        pytest.fail("descendant survived its exited leader")


STUB = Path(__file__).parents[1] / "fixtures" / "worker_stub.py"


async def test_inspection_failure_and_notification_failure_release_everything(tmp_path: Path) -> None:
    registry = RequestRegistry()
    cleaned: list[str] = []

    async def status(request, stage):
        raise RuntimeError("Telegram unavailable")

    async def never(*args):
        raise AssertionError("workflow should stop after failed status notification")

    async def cleanup(request):
        cleaned.append(request.request_id)

    workflow = MediaWorkflow(
        registry,
        inspect=never,
        publish_preview=never,
        download=never,
        deliver=never,
        status=status,
        cleanup=cleanup,
        max_file_bytes=50_000_000,
    )
    with pytest.raises(RuntimeError, match="Telegram unavailable"):
        await workflow.submit(
            user_id=1,
            chat_id=1,
            text="https://youtu.be/abcDEF12345",
            chat_type="private",
        )
    assert registry.active_work_count == 0
    assert registry.pending_count == 0
    assert len(cleaned) == 1
    assert registry.terminal(cleaned[0]).state is RequestState.FAILED  # type: ignore[union-attr]


def test_startup_sweeper_removes_only_stale_request_directories(tmp_path: Path) -> None:
    stale = tmp_path / ("a" * 32 + "-stale")
    recent = tmp_path / ("b" * 32 + "-recent")
    unrelated = tmp_path / "keep-me"
    for path in (stale, recent, unrelated):
        path.mkdir()
        (path / "file").write_bytes(b"x")
    os.utime(stale, (0, 0))
    removed = sweep_work_directories(tmp_path, older_than=900, wall_time=lambda: 1000)
    assert removed == [stale]
    assert not stale.exists()
    assert recent.exists()
    assert unrelated.exists()


async def test_real_process_group_timeout_is_reaped_before_cleanup(tmp_path: Path) -> None:
    marker = tmp_path / "late-write"
    supervisor = WorkerSupervisor(
        [sys.executable, str(STUB)],
        termination_grace=0.05,
    )
    with pytest.raises(WorkerTimeout):
        await supervisor.run(
            "download",
            {"mode": "hang", "marker": str(marker)},
            timeout=0.05,
        )
    await __import__("asyncio").sleep(0.1)
    assert not marker.exists()


async def test_worker_diagnostics_redact_signed_urls_and_bot_tokens() -> None:
    supervisor = WorkerSupervisor([sys.executable, str(STUB)])
    assert await supervisor.run(
        "download", {"mode": "sensitive_stderr"}, timeout=1
    ) is True
    diagnostic = supervisor.last_stderr.decode("utf-8")
    assert "signed-secret" not in diagnostic
    assert "abcdefghijklmnopqrstuvwxyzABCDE" not in diagnostic
    assert "https://" not in diagnostic
    assert diagnostic == "download failed for <redacted-url> TELEGRAM_BOT_TOKEN=<redacted>"


@pytest.mark.parametrize("mode", ["malformed", "oversized"])
async def test_malformed_or_storage_sized_worker_output_is_terminal(mode: str) -> None:
    supervisor = WorkerSupervisor([sys.executable, str(STUB)])
    with pytest.raises(Exception):
        await supervisor.run("inspect", {"mode": mode}, timeout=1)


@pytest.mark.parametrize(("stage", "failure"), [
    ("checking", "timeout"), ("downloading", "timeout"), ("sending", "timeout"),
    ("checking", "cancel"), ("downloading", "cancel"), ("sending", "cancel"),
    ("downloading", "storage"), ("downloading", "oversize"),
    ("sending", "failed"), ("sending", "unknown"),
])
async def test_music_failures_release_capacity_clean_files_and_never_resend(tmp_path, monkeypatch, stage, failure):
    import asyncio
    from unittest.mock import AsyncMock
    from types import SimpleNamespace
    from openmedia.delivery import deliver_media
    from openmedia.models import DeliveryResult, FormatOption, MediaMetadata
    from openmedia.sources import DownloadResult, InspectResult

    now = [10.0]
    registry = RequestRegistry(monotonic=lambda: now[0])
    url = "https://music.youtube.com/watch?v=abcDEF12345"
    metadata = MediaMetadata("youtube", url, "abcDEF12345", media_kind="audio")
    option = FormatOption(0, "yt_dlp", "140", "audio", "m4a", "audio/mp4")
    budgets = []
    actual_timeout = asyncio.timeout
    def timeout(delay):
        budgets.append(delay)
        return actual_timeout(delay)
    monkeypatch.setattr("openmedia.coordinator.asyncio.timeout", timeout)
    path = tmp_path / "selected.m4a"
    observed, sends = [], []

    def fail(here):
        if here != stage:
            return
        if failure == "timeout":
            raise TimeoutError()
        if failure == "cancel":
            raise asyncio.CancelledError()
        if failure == "storage":
            raise OSError(28, "temporary space exhausted")

    async def inspect(request):
        observed.append(request)
        path.write_bytes(b"inspection scratch")
        fail("checking")
        now[0] = 20
        return InspectResult(metadata, (option,))

    async def download(request, selected):
        assert request.processing_deadline == 620
        path.write_bytes(b"x" * (51 if failure == "oversize" else 7))
        fail("downloading")
        if failure == "oversize":
            from openmedia.workers import WorkerRemoteError
            raise WorkerRemoteError("too_large", "download")
        return DownloadResult(path, path.stat().st_size, metadata.media_id, "140", "audio", "m4a", "audio/mp4")

    async def send_document(**kwargs):
        sends.append(kwargs["document"].read())
        return SimpleNamespace(message_id=99, document=object())

    async def deliver(request, result):
        fail("sending")
        if failure in {"failed", "unknown"}:
            sends.append(result.path.read_bytes())
            return DeliveryResult(status=failure, error_category="upload_failed" if failure == "failed" else "upload_ambiguous",
                failed_stage="sending", next_step="Check this chat before submitting the link again.")
        return await deliver_media(SimpleNamespace(send_document=send_document), request=request,
            downloaded=result, owned_directory=tmp_path, max_file_bytes=50,
            deadline=request.processing_deadline, monotonic=lambda: now[0])

    async def cleanup(request):
        path.unlink(missing_ok=True)

    notify = AsyncMock()
    workflow = MediaWorkflow(registry, inspect=inspect, publish_preview=AsyncMock(return_value=55),
        download=download, deliver=deliver, status=AsyncMock(), cleanup=cleanup,
        notify_failure=notify, max_file_bytes=50)
    if failure == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await workflow.submit(user_id=7, chat_id=77, text=url, chat_type="private")
    elif stage == "checking":
        with pytest.raises(TimeoutError):
            await workflow.submit(user_id=7, chat_id=77, text=url, chat_type="private")
    else:
        await workflow.submit(user_id=7, chat_id=77, text=url, chat_type="private")
    assert registry.terminal(observed[0].request_id).state is RequestState.FAILED
    result = observed[0].delivery_result
    assert result is not None
    assert result.status == ("unknown" if stage == "sending" and failure in {"timeout", "cancel", "unknown"} else "failed")
    assert registry.active_work_count == registry.pending_count == 0
    assert not path.exists()
    assert len(sends) == (1 if failure in {"failed", "unknown"} else 0)
    assert notify.await_count == (0 if failure == "cancel" else 1)
    assert budgets[0] == 55  # 60-second inspection less the five-second reap reserve.
    if stage != "checking":
        assert budgets[1] == 595  # Original 600-second processing budget, same reserve.
    if failure == "oversize":
        assert result.error_category == "too_large"
    if failure == "storage":
        assert result.error_category == "storage_exhausted"
    if result.status == "unknown":
        assert "Check this chat" in result.next_step


async def test_shutdown_cancels_music_download_and_cleans_owned_file(tmp_path, monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    from telegram.ext import Application, ApplicationBuilder
    from openmedia.__main__ import ManagedApplication
    from openmedia.models import FormatOption, MediaMetadata
    from openmedia.sources import InspectResult

    app = ApplicationBuilder().application_class(ManagedApplication).token("123456789:offline").build()
    registry = RequestRegistry(monotonic=lambda: 10)
    url = "https://music.youtube.com/watch?v=abcDEF12345"
    metadata = MediaMetadata("youtube", url, "abcDEF12345", media_kind="audio")
    option = FormatOption(0, "yt_dlp", "140", "audio", "m4a", "audio/mp4")
    started = asyncio.Event()
    path = tmp_path / "selected.m4a"
    async def download(item, selected):
        path.write_bytes(b"partial")
        started.set()
        await asyncio.Event().wait()
    async def cleanup(item):
        path.unlink(missing_ok=True)
    deliver = AsyncMock()
    workflow = MediaWorkflow(registry, inspect=AsyncMock(return_value=InspectResult(metadata, (option,))),
        publish_preview=AsyncMock(return_value=55), download=download, deliver=deliver,
        status=AsyncMock(), cleanup=cleanup, max_file_bytes=50_000_000)
    job = app.create_task(workflow.submit(user_id=7, chat_id=77, text=url, chat_type="private"))
    await started.wait()
    monkeypatch.setattr(Application, "stop", AsyncMock())
    await app.stop()
    assert job.cancelled()
    assert not path.exists()
    assert registry.active_work_count == registry.pending_count == 0
    deliver.assert_not_awaited()


def test_music_unknown_size_source_output_is_stopped_at_guarded_byte_cap(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from openmedia.models import FormatOption, MediaMetadata
    from openmedia.network import ResponseTooLarge
    from openmedia.sources import DownloadInput
    from openmedia.sources.ytdlp import YtDlpAdapter
    from tests.integration.test_refresh import Script

    url = "https://music.youtube.com/watch?v=abcDEF12345"
    option = FormatOption(0, "yt_dlp", "140", "audio", "m4a", "audio/mp4",
        transport_ref={"url": "https://cdn.invalid/audio", "vcodec": "none", "acodec": "mp4a"})
    script = Script(monkeypatch, tmp_path, [(200, b"x" * 101)])
    monkeypatch.setattr("openmedia.network.time.monotonic", lambda: 10)
    with pytest.raises(ResponseTooLarge):
        YtDlpAdapter().download(DownloadInput("a" * 32,
            MediaMetadata("youtube", url, "abcDEF12345", media_kind="audio"), option,
            tmp_path, 100, 100, 1000), transport=script.transport,
            rate_control=SimpleNamespace(acquire=lambda *args, **kwargs: None))
    assert not (tmp_path / "selected.m4a").exists()
    assert script.urls == ["https://cdn.invalid/audio"]


@pytest.mark.parametrize("stage", ["checking", "downloading", "sending"])
async def test_music_workflow_deadline_cancels_stalled_callbacks(tmp_path, monkeypatch, stage):
    import asyncio
    from unittest.mock import AsyncMock
    from openmedia.models import FormatOption, MediaMetadata
    from openmedia.sources import DownloadResult, InspectResult

    # Keep asyncio's actual cancellation/TimeoutError conversion, but schedule expiry
    # from a controlled monotonic clock instead of waiting for wall-clock time.
    now = [10.0]
    active = []
    budgets = []
    real_timeout = asyncio.timeout

    class ScheduledTimeout:
        def __init__(self, delay):
            self.deadline = now[0] + delay
            self.guard = real_timeout(None)
            budgets.append(delay)

        async def __aenter__(self):
            await self.guard.__aenter__()
            active.append(self)
            return self

        async def __aexit__(self, *args):
            active.remove(self)
            return await self.guard.__aexit__(*args)

    monkeypatch.setattr("openmedia.coordinator.asyncio.timeout", ScheduledTimeout)
    registry = RequestRegistry(monotonic=lambda: now[0])
    url = "https://music.youtube.com/watch?v=abcDEF12345"
    metadata = MediaMetadata("youtube", url, "abcDEF12345", media_kind="audio")
    option = FormatOption(0, "yt_dlp", "140", "audio", "m4a", "audio/mp4")
    path = tmp_path / "selected.m4a"
    observed, cancelled, uploads = [], [], []

    async def stall(here, expected_deadline):
        assert len(active) == 1, "workflow must guard the stalled operation"
        assert active[0].deadline == expected_deadline
        now[0] = expected_deadline
        active[0].guard.reschedule(asyncio.get_running_loop().time())
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append(here)
            raise

    async def status(request, here):
        if here == "checking":
            observed.append(request)
            now[0] += 7  # Checking status consumes the inspection budget.
        elif here == "downloading":
            assert request.processing_deadline == 620
            now[0] += 13  # Status consumes the shared processing budget.

    async def inspect(request):
        path.write_bytes(b"inspection scratch")
        if stage == "checking":
            await stall("checking", 65)  # created 10 + 60 - 5 reserve.
        now[0] = 20
        return InspectResult(metadata, (option,))

    async def download(request, selected):
        path.write_bytes(b"partial")
        if stage == "downloading":
            await stall("downloading", 615)
        now[0] += 200  # Download time must not reset the send deadline.
        return DownloadResult(path, 7, metadata.media_id, "140", "audio", "m4a", "audio/mp4")

    async def deliver(request, result):
        uploads.append(result.path.read_bytes())
        assert now[0] == 233
        await stall("sending", 615)

    async def cleanup(request):
        path.unlink(missing_ok=True)

    notify = AsyncMock()
    workflow = MediaWorkflow(registry, inspect=inspect, publish_preview=AsyncMock(return_value=55),
        download=download, deliver=deliver, status=status, cleanup=cleanup,
        notify_failure=notify, max_file_bytes=50_000_000)
    if stage == "checking":
        with pytest.raises(TimeoutError):
            await workflow.submit(user_id=7, chat_id=77, text=url, chat_type="private")
    else:
        await workflow.submit(user_id=7, chat_id=77, text=url, chat_type="private")
    request = observed[0]
    assert cancelled == [stage]
    assert budgets == ([55, 5] if stage == "checking" else [55, 595, 5])
    assert request.delivery_result.error_category == "timeout"
    assert request.delivery_result.failed_stage == stage
    assert request.delivery_result.status == ("unknown" if stage == "sending" else "failed")
    assert registry.terminal(request.request_id).state is RequestState.FAILED
    assert registry.active_work_count == registry.pending_count == 0
    assert not path.exists()
    assert notify.await_count == 1
    assert len(uploads) == (1 if stage == "sending" else 0)
    if stage == "sending":
        assert "Check this chat" in request.delivery_result.next_step
        # A replay cannot claim the terminal request and resend the uncertain file.
        from openmedia.coordinator import WorkflowBusy
        with pytest.raises(WorkflowBusy):
            await workflow.select(request_id=request.request_id, user_id=7, chat_id=77,
                preview_message_id=55, option_id=0)
        assert len(uploads) == 1
