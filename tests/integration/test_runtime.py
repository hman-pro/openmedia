from __future__ import annotations

import json
import logging
import io
from pathlib import Path

import pytest

import openmedia.__main__ as runtime
from openmedia.config import ConfigError, Settings


@pytest.mark.parametrize("level", ["INFO", "DEBUG"])
async def test_parent_logs_redact_transport_and_exception_secrets(level):
    import httpx
    token = "123456789:offline-test-secret"
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(runtime.SafeLogFormatter("%(message)s", secrets=(token,)))
    logger = logging.getLogger("httpx")
    previous = logger.level
    logger.setLevel(level)
    logger.addHandler(handler)
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as client:
            await client.get(f"https://api.telegram.org/bot{token}/getMe")
        try:
            raise RuntimeError(f"credential={token} https://cdn.example/media?signature=secret")
        except RuntimeError:
            logger.exception("request failed")
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
    assert token not in output.getvalue()
    assert "signature=secret" not in output.getvalue()
    assert "request failed" in output.getvalue()


async def test_application_stop_cancels_tracked_work_before_waiting(monkeypatch):
    import asyncio
    from telegram.ext import ApplicationBuilder, Application
    from unittest.mock import AsyncMock
    app = ApplicationBuilder().application_class(runtime.ManagedApplication).token("123456789:offline").build()
    cleanup = asyncio.Event()
    async def work():
        try:
            await asyncio.Event().wait()
        finally:
            cleanup.set()
    job = app.create_task(work(), name="openmedia-download")
    await asyncio.sleep(0)
    monkeypatch.setattr(Application, "stop", AsyncMock())
    await asyncio.wait_for(app.stop(), 0.2)
    assert job.cancelled() and cleanup.is_set()


async def test_application_stop_reaps_active_source_child(tmp_path, monkeypatch):
    import asyncio, sys
    from telegram.ext import ApplicationBuilder, Application
    from unittest.mock import AsyncMock
    from openmedia.workers import WorkerSupervisor
    app = ApplicationBuilder().application_class(runtime.ManagedApplication).token("123456789:offline").build()
    supervisor = WorkerSupervisor([sys.executable, "-c", "import time; time.sleep(60)"], termination_grace=0.05)
    job = app.create_task(supervisor.run("inspect", {}, timeout=60))
    await asyncio.sleep(0.05)
    monkeypatch.setattr(Application, "stop", AsyncMock())
    await asyncio.wait_for(app.stop(), 0.5)
    assert job.cancelled()


async def test_shutdown_reaps_real_child_group_cleans_workspace_and_removes_health(tmp_path, monkeypatch):
    import asyncio, os, re, sys, time
    from telegram.ext import Application
    from unittest.mock import AsyncMock
    from openmedia.coordinator import AdmissionOutcome, MediaWorkflow
    from openmedia.workers import WorkerSupervisor
    settings = Settings.from_env(environment(tmp_path))
    app, registry = runtime.build_application(settings)
    callbacks = app.bot_data["openmedia_callbacks"]
    pids = tmp_path / "pids"
    script = ("import os,subprocess,sys,time;"
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']);"
        f"open({str(pids)!r},'w').write(f'{{os.getpid()}} {{child.pid}}');time.sleep(60)")
    callbacks.supervisor = WorkerSupervisor([sys.executable, "-c", script], termination_grace=0.2)
    monkeypatch.setattr(runtime.HealthTrackingBot, "send_message", AsyncMock(), raising=False)
    workflow = MediaWorkflow(registry, inspect=callbacks.inspect, publish_preview=callbacks.preview,
        download=callbacks.download, deliver=callbacks.deliver, status=callbacks.status,
        cleanup=callbacks.cleanup, notify_failure=callbacks.notify_failure)
    await app.post_init(app)
    health = app.bot_data["openmedia_health"]
    health.record_successful_poll()
    job = app.create_task(workflow.submit(user_id=1, chat_id=1,
        text="https://youtu.be/abcDEF12345", chat_type="private"), name="openmedia-inspect")
    for _ in range(250):
        if pids.exists() and len(pids.read_text().split()) == 2:
            break
        await asyncio.sleep(0.02)
    leader, descendant = (int(value) for value in pids.read_text().split())
    workspaces = lambda: [child for child in tmp_path.iterdir() if re.match(r"^[0-9a-f]{32}-", child.name)]
    assert workspaces() and health.path.exists()

    monkeypatch.setattr(Application, "stop", AsyncMock())
    started = time.monotonic()
    await app.stop()
    await app.post_shutdown(app)
    assert time.monotonic() - started < 20
    assert job.cancelled()
    for pid in (leader, descendant):
        for _ in range(100):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            await asyncio.sleep(0.02)
        else:
            pytest.fail("source worker process group survived shutdown")
    assert not workspaces() and not health.path.exists()
    assert app.bot_data["openmedia_maintenance"].done()
    late = registry.new_request(user_id=2, chat_id=2, source_url="https://youtu.be/abcDEF12345",
        platform="youtube", media_id="abcDEF12345")
    assert (await registry.admit(late)).outcome is AdmissionOutcome.WORK_BUSY


@pytest.mark.parametrize("stuck", ["work", "telegram"])
async def test_application_stop_never_raises_past_its_budget(monkeypatch, stuck):
    """A raised stop() makes PTB skip shutdown() and post_shutdown, stranding health state."""
    import asyncio
    from types import SimpleNamespace
    from telegram.ext import ApplicationBuilder, Application
    from unittest.mock import AsyncMock
    app = ApplicationBuilder().application_class(runtime.ManagedApplication).token("123456789:offline").build()
    killed = []
    app.bot_data["openmedia_callbacks"] = SimpleNamespace(
        supervisor=SimpleNamespace(kill_active=lambda: killed.append(True)))
    monkeypatch.setattr(runtime, "SHUTDOWN_WORK_SECONDS", 0.05)
    monkeypatch.setattr(runtime, "SHUTDOWN_KILL_SECONDS", 0.05)
    monkeypatch.setattr(runtime, "SHUTDOWN_STOP_SECONDS", 0.05)
    release = asyncio.Event()
    async def stubborn():
        while not release.is_set():
            try:
                await release.wait()
            except asyncio.CancelledError:
                pass
    async def hang(self):
        await asyncio.sleep(60)
    parent_stop = AsyncMock()
    monkeypatch.setattr(Application, "stop", hang if stuck == "telegram" else parent_stop)
    job = app.create_task(stubborn()) if stuck == "work" else None
    await asyncio.sleep(0)
    await asyncio.wait_for(app.stop(), 1)
    if job is not None:
        assert killed
        parent_stop.assert_awaited_once()
        release.set()
        await job


async def test_send_limiter_covers_bot_send_and_edit_and_expires_state(tmp_path, monkeypatch):
    from telegram.ext import ExtBot
    from unittest.mock import AsyncMock
    clock = [0.0]
    async def sleep(delay):
        clock[0] += delay
    monkeypatch.setattr(runtime.asyncio, "sleep", sleep)
    monkeypatch.setattr(ExtBot, "_send_message", AsyncMock(return_value=True))
    bot = runtime.HealthTrackingBot(token="123456789:offline", runtime_health=runtime.RuntimeHealth(tmp_path / "health"))
    bot._ordinary_messages.monotonic = lambda: clock[0]
    await bot._send_message("sendMessage", {"chat_id": 1})
    await bot._send_message("editMessageText", {"chat_id": 1})
    assert clock[0] == 1
    for chat in range(2, 24):
        await bot._send_message("sendMessage", {"chat_id": chat})
    assert clock[0] >= 2
    clock[0] = 10
    await bot._send_message("sendMessage", {"chat_id": 99})
    assert set(bot._ordinary_messages._chat_next) == {99}


def assert_send_bounds(schedule):
    """schedule: (chat_id, send_time) pairs. Enforce 1/s per chat and 20/s overall."""
    times = sorted(stamp for _chat, stamp in schedule)
    for index in range(len(times) - 20):
        assert times[index + 20] - times[index] >= 1.0, "more than 20 ordinary sends inside one second"
    by_chat = {}
    for chat, stamp in schedule:
        by_chat.setdefault(chat, []).append(stamp)
    for stamps in by_chat.values():
        stamps.sort()
        assert all(later - earlier >= 1.0 for earlier, later in zip(stamps, stamps[1:]))


def test_send_limiter_bounds_concurrent_users_without_needless_delay():
    limiter = runtime.OrdinaryMessageLimiter()
    schedule = [(chat, limiter.reserve(chat, 0.0)) for chat in range(50)]
    assert_send_bounds(schedule)
    assert [stamp for _chat, stamp in schedule[:20]] == [0.0] * 20
    assert max(stamp for _chat, stamp in schedule) == 2.0  # 50 sends need exactly three one-second slots


def test_send_limiter_repeated_invalid_input_only_delays_its_own_chat():
    limiter = runtime.OrdinaryMessageLimiter()
    spam = [(1, limiter.reserve(1, 0.0)) for _ in range(30)]
    assert [stamp for _chat, stamp in spam] == [float(second) for second in range(30)]
    others = [(chat, limiter.reserve(chat, 0.5)) for chat in range(2, 40)]
    assert_send_bounds(spam + others)
    assert sum(stamp == 0.5 for _chat, stamp in others) == 19  # 20/s minus the spammer's own slot
    assert max(stamp for _chat, stamp in others) <= 2.5


async def test_send_limiter_does_not_hold_other_chats_behind_a_waiting_chat(monkeypatch):
    import asyncio
    limiter = runtime.OrdinaryMessageLimiter(monotonic=lambda: 0.0)
    release = asyncio.Event()
    async def sleep(delay):
        await release.wait()
    monkeypatch.setattr(runtime.asyncio, "sleep", sleep)
    sent = []
    async def send(chat):
        sent.append(chat)
    await limiter.run(1, lambda: send(1))
    waiting = asyncio.ensure_future(limiter.run(1, lambda: send(1)))
    await asyncio.wait({waiting}, timeout=0.05)  # let chat 1 reach its one-second wait first
    await asyncio.wait_for(limiter.run(2, lambda: send(2)), 0.5)
    assert sent == [1, 2] and not waiting.done()
    release.set()
    await waiting
    assert sent == [1, 2, 1]


async def test_transient_cleanup_retries_on_next_sweep(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from openmedia.coordinator import RequestRegistry
    settings = Settings.from_env(environment(tmp_path))
    callbacks = runtime.RuntimeCallbacks(settings, SimpleNamespace())
    directory = tmp_path / ("a" * 32 + "-retry"); directory.mkdir()
    actual = runtime.cleanup_request_directory
    attempts = []
    def cleanup(path, **kwargs):
        attempts.append(path)
        if len(attempts) == 1:
            raise OSError("temporary failure")
        return actual(path, **kwargs)
    monkeypatch.setattr(runtime, "cleanup_request_directory", cleanup)
    request = SimpleNamespace(work_directory=directory)
    await callbacks.cleanup(request)
    sleeps = 0
    async def sleep(seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            raise asyncio.CancelledError
    monkeypatch.setattr(runtime.asyncio, "sleep", sleep)
    with pytest.raises(asyncio.CancelledError):
        await callbacks.maintain(RequestRegistry())
    assert not directory.exists() and not callbacks.failed_cleanup


async def test_maintenance_loop_survives_unexpected_sweep_and_retry_failures(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from openmedia.coordinator import RequestRegistry
    settings = Settings.from_env(environment(tmp_path))
    callbacks = runtime.RuntimeCallbacks(settings, SimpleNamespace())
    callbacks.failed_cleanup.add(tmp_path / "outside" / "not-a-workspace")
    sweeps = []
    def sweep(root, **kwargs):
        sweeps.append(kwargs["older_than"])
        if len(sweeps) == 1:
            raise ValueError("workspace root cannot be a symlink")
        return []
    monkeypatch.setattr(runtime, "sweep_work_directories", sweep)
    ticks = 0
    async def sleep(seconds):
        nonlocal ticks
        ticks += 1
        if ticks == 3:
            raise asyncio.CancelledError
    monkeypatch.setattr(runtime.asyncio, "sleep", sleep)
    with pytest.raises(asyncio.CancelledError):
        await callbacks.maintain(RequestRegistry())
    assert len(sweeps) == 2


def test_worst_case_sweep_alignment_stays_inside_cleanup_ceiling(tmp_path):
    from openmedia.workers import sweep_work_directories
    settings = Settings.from_env(environment(tmp_path))
    ceiling = settings.cleanup_seconds
    threshold = runtime.sweep_threshold(ceiling)
    interval = runtime.SWEEP_INTERVAL_SECONDS
    # A sweep can miss the threshold by an instant, and one tick may drift by a full interval.
    assert threshold + 2 * interval <= ceiling
    assert threshold > settings.processing_seconds  # never sweep a workspace still in use
    directory = tmp_path / ("a" * 32 + "-late")
    directory.mkdir()
    created = directory.lstat().st_mtime
    missed = created + threshold - 0.001
    assert sweep_work_directories(tmp_path, older_than=threshold, wall_time=lambda: missed) == []
    next_tick = missed + interval
    assert sweep_work_directories(tmp_path, older_than=threshold, wall_time=lambda: next_tick) == [directory]
    assert next_tick - created < ceiling - interval


async def test_timing_events_record_measured_preview_ack_and_upstream(tmp_path, caplog):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from openmedia.coordinator import RequestRegistry
    from openmedia.models import MediaMetadata, FormatOption
    from openmedia.sources import InspectResult
    callbacks = runtime.RuntimeCallbacks(Settings.from_env(environment(tmp_path)),
        SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=1)))))
    request = RequestRegistry().new_request(user_id=1, chat_id=1, source_url="https://youtu.be/abcDEF12345", platform="youtube", media_id="abcDEF12345")
    with caplog.at_level("INFO", logger="openmedia"):
        await callbacks.status(request, "checking")
        await callbacks.preview(request, InspectResult(MediaMetadata("youtube", request.source_url, request.media_id),
            (FormatOption(0, "fixture", "v", "video", "mp4", "video/mp4", includes_audio=True),)))
        callbacks.upstream(request, {"upstream_status_class": "429"})
    events = [json.loads(record.message) for record in caplog.records]
    assert {event["stage"] for event in events} >= {"acknowledgment", "preview", "source_response"}
    assert all(event["elapsed_seconds"] >= 0 for event in events)
    assert events[-1]["upstream_status_class"] == "429"


class _StopWorker(Exception):
    pass


async def test_workers_receive_request_deadline_less_reap_reserve(tmp_path):
    """A rate delay that would cross the request deadline is refused, not left to time out."""
    import time
    from types import SimpleNamespace
    from openmedia.coordinator import RequestRegistry
    from openmedia.models import FormatOption, MediaMetadata
    callbacks = runtime.RuntimeCallbacks(Settings.from_env(environment(tmp_path)), SimpleNamespace(bot=None))
    registry = RequestRegistry()
    request = registry.new_request(user_id=1, chat_id=1, source_url="https://youtu.be/abcDEF12345", platform="youtube", media_id="abcDEF12345")
    request.created_at = time.monotonic() - 50  # 10s of the 60s inspection deadline remain
    callbacks.rate._cooldown_until["youtube"] = time.monotonic() + 8  # ends after deadline - reserve
    seen = {}

    async def run(operation, payload, *, timeout, on_rate_request, **kwargs):
        seen[operation] = (payload["deadline"], timeout)
        seen[f"{operation}-rate"] = await on_rate_request(
            {"platform": "youtube", "request_class": "metadata", "deadline": payload["deadline"]})
        raise _StopWorker

    callbacks.supervisor.run = run
    with pytest.raises(_StopWorker):
        await callbacks.inspect(request)
    deadline, timeout = seen["inspect"]
    assert deadline == pytest.approx(request.created_at + 60 - 5)
    assert timeout == pytest.approx(request.created_at + 60 - time.monotonic(), abs=0.5)
    assert seen["inspect-rate"] == {"allowed": False, "delay": 0}

    await registry.admit(request)
    option = FormatOption(0, "yt_dlp", "18", "video", "mp4", "video/mp4", includes_audio=True)
    await registry.publish_preview(request.request_id, metadata=MediaMetadata("youtube", request.source_url, request.media_id),
        options=(option,), preview_message_id=9)
    await registry.claim_selection(request.request_id, user_id=1, chat_id=1, preview_message_id=9, option_id=0)
    request.processing_deadline = time.monotonic() + 10
    with pytest.raises(_StopWorker):
        await callbacks.download(request, option)
    deadline, timeout = seen["download"]
    assert deadline == pytest.approx(request.processing_deadline - 5)
    assert timeout == pytest.approx(request.processing_deadline - time.monotonic(), abs=0.5)
    assert seen["download-rate"] == {"allowed": False, "delay": 0}


async def test_downloading_status_names_the_selected_option(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from openmedia.coordinator import RequestRegistry
    from openmedia.models import FormatOption, MediaMetadata
    send = AsyncMock(return_value=SimpleNamespace(message_id=1))
    callbacks = runtime.RuntimeCallbacks(Settings.from_env(environment(tmp_path)),
        SimpleNamespace(bot=SimpleNamespace(send_message=send)))
    registry = RequestRegistry()
    request = registry.new_request(user_id=1, chat_id=1, source_url="https://youtu.be/abcDEF12345", platform="youtube", media_id="abcDEF12345")
    await registry.admit(request)
    option = FormatOption(3, "fixture", "140", "audio", "m4a", "audio/mp4", bitrate=129.5)
    await registry.publish_preview(request.request_id, metadata=MediaMetadata("youtube", request.source_url, request.media_id),
        options=(option,), preview_message_id=9)
    await registry.claim_selection(request.request_id, user_id=1, chat_id=1, preview_message_id=9, option_id=3)
    await callbacks.status(request, "downloading")
    assert "4. audio · M4A · 129.5 kbps" in send.await_args.kwargs["text"]


async def test_request_logs_separate_service_timing_from_external_failures(tmp_path, caplog):
    """Quickstart exclusion rule: only logged 429/5xx/retry_after/connection failures excuse a sample."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from openmedia.coordinator import RequestRegistry
    from openmedia.models import DeliveryResult
    callbacks = runtime.RuntimeCallbacks(Settings.from_env(environment(tmp_path)),
        SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=1)))))
    registry = RequestRegistry()
    make = lambda user: registry.new_request(user_id=user, chat_id=user,
        source_url="https://youtu.be/abcDEF12345", platform="youtube", media_id="abcDEF12345")
    slow, outage, client_error = make(1), make(2), make(3)
    failed = DeliveryResult(status="failed", error_category="timeout", failed_stage="checking", next_step="Retry later.")
    with caplog.at_level("INFO", logger="openmedia"):
        callbacks.upstream(slow, {"upstream_status_class": "2xx"})
        await callbacks.notify_failure(slow, failed)
        callbacks.upstream(outage, {"upstream_status_class": "5xx"})
        callbacks.external_failure(outage.request_id, "retry_after")
        await callbacks.notify_failure(outage, failed)
        callbacks.upstream(client_error, {"upstream_status_class": "4xx"})
        callbacks.upstream(client_error, {"upstream_status_class": "https://signed.invalid/?sig=secret"})
        await callbacks.notify_failure(client_error, failed)
    events = [json.loads(record.message) for record in caplog.records]
    terminal = {event["request_id"]: event for event in events if event["stage"] == "terminal"}
    assert terminal[slow.request_id]["external_causes"] == []
    assert terminal[outage.request_id]["external_causes"] == ["5xx", "retry_after"]
    assert terminal[client_error.request_id]["external_causes"] == []
    assert "signed.invalid" not in caplog.text
    assert callbacks._external == {}, "per-request cause state is released at the terminal record"


async def test_confirmed_delivery_logs_measured_selection_time_and_terminal_outcome(tmp_path, caplog, monkeypatch):
    import time
    from types import SimpleNamespace
    from openmedia.coordinator import RequestRegistry
    from openmedia.models import DeliveryResult
    settings = Settings.from_env(environment(tmp_path))
    callbacks = runtime.RuntimeCallbacks(settings, SimpleNamespace(bot=SimpleNamespace()))
    request = RequestRegistry().new_request(user_id=1, chat_id=1, source_url="https://youtu.be/abcDEF12345",
        platform="youtube", media_id="abcDEF12345")
    request.work_directory = tmp_path
    request.processing_deadline = time.monotonic() + settings.processing_seconds - 7.5  # selected 7.5s ago
    async def deliver(*args, **kwargs):
        return DeliveryResult(status="confirmed", message_id=5, actual_bytes=7)
    monkeypatch.setattr(runtime, "deliver_document", deliver)
    with caplog.at_level("INFO", logger="openmedia"):
        await callbacks.deliver(request, SimpleNamespace())
    events = {event["stage"]: event for event in (json.loads(record.message) for record in caplog.records)}
    assert 7.5 <= events["delivery"]["selected_elapsed_seconds"] < 8.5
    assert events["terminal"]["outcome"] == "confirmed" and events["terminal"]["external_causes"] == []


@pytest.mark.parametrize("error, expected", [("retry_after", "retry_after"), ("network", "connection_failure"),
    ("bad_request", None)])
async def test_telegram_failures_are_attributed_only_when_external(tmp_path, monkeypatch, error, expected):
    from telegram.error import BadRequest, NetworkError, RetryAfter
    from telegram.ext import ExtBot
    from unittest.mock import AsyncMock
    raised = {"retry_after": lambda: RetryAfter(3), "network": lambda: NetworkError("Bad Gateway"),
        "bad_request": lambda: BadRequest("Message is not modified")}[error]()
    monkeypatch.setattr(ExtBot, "_send_message", AsyncMock(side_effect=raised))
    bot = runtime.HealthTrackingBot(token="123456789:offline", runtime_health=runtime.RuntimeHealth(tmp_path / "health"))
    seen = []
    bot.external_observers.append(lambda request_id, cause: seen.append((request_id, cause)))
    token = runtime.REQUEST_CONTEXT.set("a" * 32)
    try:
        with pytest.raises(type(raised)):
            await bot._send_message("sendMessage", {"chat_id": 1})
    finally:
        runtime.REQUEST_CONTEXT.reset(token)
    assert seen == ([("a" * 32, expected)] if expected else [])


def environment(work_dir: Path, token: str = "123456789:test-token-value") -> dict[str, str]:
    return {
        "TELEGRAM_BOT_TOKEN": token,
        "OPENMEDIA_WORK_DIR": str(work_dir),
    }


def test_check_config_is_local_and_redacts_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    token = "123456789:never-print-this-token"
    settings = Settings.from_env(environment(tmp_path, token))
    monkeypatch.setattr(runtime.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(runtime.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(runtime, "build_application", lambda settings: pytest.fail("must not poll"))
    assert runtime.main(["--check-config"]) == 0
    captured = capsys.readouterr()
    assert token not in captured.out + captured.err
    assert "<redacted>" in captured.out


def test_check_config_keeps_workspaces_but_polling_startup_sweeps_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings.from_env(environment(tmp_path))
    monkeypatch.setattr(runtime.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(runtime.shutil, "which", lambda name: f"/usr/bin/{name}")
    workspace = tmp_path / ("b" * 32 + "-in-flight")
    workspace.mkdir()
    (workspace / "selected.mp4").write_bytes(b"partial")

    assert runtime.main(["--check-config"]) == 0
    assert workspace.exists(), "check-config must not delete another process's workspace"

    polled: list[bool] = []
    class FakeApplication:
        def run_polling(self, **kwargs):
            polled.append(workspace.exists())
    monkeypatch.setattr(runtime, "build_application", lambda settings: (FakeApplication(), None))
    assert runtime.main([]) == 0
    assert polled == [False], "stale workspaces are removed before polling starts"


def test_runtime_requires_bundled_ejs_challenge_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    settings = Settings.from_env(environment(tmp_path, "123456789:never-print-this-token"))
    monkeypatch.setattr(runtime.shutil, "which", lambda name: f"/bin/{name}")
    real_find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec",
        lambda name, *args: None if name == "yt_dlp_ejs" else real_find_spec(name, *args))
    with pytest.raises(ConfigError, match="EJS") as caught:
        runtime.validate_local_runtime(settings)
    assert "never-print-this-token" not in str(caught.value)
    monkeypatch.setattr(importlib.util, "find_spec", real_find_spec)
    runtime.validate_local_runtime(settings)


def test_runtime_requires_bundled_deno_ffmpeg_and_ffprobe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings.from_env(environment(tmp_path))
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None if name == "deno" else f"/bin/{name}")
    with pytest.raises(ConfigError, match="deno"):
        runtime.validate_local_runtime(settings)


@pytest.mark.parametrize(
    ("heartbeat", "last_poll", "expected", "reason"),
    [
        (199.0, 198.0, True, "healthy"),
        (109.0, 198.0, False, "heartbeat is stale"),
        (198.0, 109.0, False, "last successful poll is stale"),
    ],
)
def test_health_requires_fresh_heartbeat_and_successful_poll(
    tmp_path: Path,
    heartbeat: float,
    last_poll: float,
    expected: bool,
    reason: str,
) -> None:
    path = tmp_path / runtime.HEALTH_FILENAME
    path.write_text(
        json.dumps(
            {
                "ready": True,
                "heartbeat": heartbeat,
                "last_successful_poll": last_poll,
            }
        ),
        encoding="utf-8",
    )
    assert runtime.check_runtime_health(path, wall_time=lambda: 200.0) == (expected, reason)


def test_healthcheck_never_builds_a_second_poller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    health = runtime.RuntimeHealth(tmp_path / runtime.HEALTH_FILENAME)
    health.record_successful_poll()
    settings = Settings.from_env(environment(tmp_path))
    monkeypatch.setattr(runtime.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(runtime, "build_application", lambda settings: pytest.fail("must not poll"))
    assert runtime.main(["--healthcheck"]) == 0


def test_runtime_health_is_atomic_private_and_removed_on_shutdown(tmp_path: Path) -> None:
    health = runtime.RuntimeHealth(tmp_path / runtime.HEALTH_FILENAME, wall_time=lambda: 50.0)
    health.record_successful_poll()
    assert health.path.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob("*.tmp-*"))
    health.remove()
    assert not health.path.exists()


def test_container_contract_is_pinned_nonroot_readonly_compatible() -> None:
    dockerfile = (Path(__file__).parents[2] / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.13.15-slim-bookworm" in dockerfile
    assert "ghcr.io/astral-sh/uv:0.12.15" in dockerfile
    assert "denoland/deno:bin-2.9.6" in dockerfile
    assert "FFMPEG_DEBIAN_VERSION=7:5.1.9-0+deb12u1" in dockerfile
    assert "uv sync --locked --no-dev" in dockerfile
    assert "import yt_dlp_ejs" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "--start-period=120s" in dockerfile
    assert "EXPOSE" not in dockerfile
    assert "OPENMEDIA_WORK_DIR=/tmp/openmedia" in dockerfile
