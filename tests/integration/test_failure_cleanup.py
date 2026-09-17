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
        publish_preview=AsyncMock(), download=AsyncMock(), deliver=AsyncMock(), status=AsyncMock(), notify_failure=notify)
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
        download=AsyncMock(), deliver=AsyncMock(), status=slow, inspection_seconds=0.03, reap_reserve=0)
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
        deliver=upload, notify_failure=notify, reap_reserve=0)
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
