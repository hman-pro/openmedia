"""Stage coverage of the diagnostic log across the request journeys (002, SC-002)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from openmedia import diagnostics
from openmedia.config import Settings
from openmedia.coordinator import MediaWorkflow, RequestRegistry
from openmedia.models import DeliveryResult, FormatOption, MediaMetadata
from openmedia.sources import DownloadResult, InspectResult
from openmedia.workers import WorkerRemoteError

TOKEN = "123456789:AAEXAMPLE-controlled-tests-only-not-a-real-token"
LINK = "https://youtu.be/abcDEF12345"
MEDIA_ID = "abcDEF12345"
OPTION = FormatOption(0, "fixture", "18", "video", "mp4", "video/mp4", includes_audio=True)
# A second kind keeps the default journey on the tapped card: one kept choice would be automatic.
AUDIO_OPTION = FormatOption(1, "fixture", "140", "audio", "m4a", "audio/mp4")
MAX_FILE_BYTES = 50_000_000
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ytdlp"


class Trace:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.stop = diagnostics.configure_diagnostics(Settings(telegram_bot_token=TOKEN,
            diagnostic_log=True, diagnostic_log_dir=directory))

    def entries(self) -> list[dict[str, Any]]:
        self.stop()
        return [json.loads(line) for path in sorted(self.directory.glob("openmedia-*.log"))
            for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def trace(tmp_path: Path) -> Iterator[Trace]:
    value = Trace(tmp_path / "logs")
    yield value
    value.stop()


def stages(entries: list[dict[str, Any]], request_id: str) -> list[str]:
    return [entry["stage"] for entry in entries if entry.get("request_id") == request_id]


def workflow_for(registry: RequestRegistry, tmp_path: Path, **overrides: Any) -> MediaWorkflow:
    path = tmp_path / "video.mp4"
    path.write_bytes(b"fixture")
    metadata = MediaMetadata("youtube", LINK, MEDIA_ID)
    callbacks: dict[str, Any] = {
        "inspect": AsyncMock(return_value=InspectResult(metadata=metadata, options=(OPTION, AUDIO_OPTION))),
        "publish_preview": AsyncMock(return_value=7),
        "download": AsyncMock(return_value=DownloadResult(path=path, media_id=MEDIA_ID,
            source_format_id="18", media_type="video", extension="mp4", mime_type="video/mp4",
            actual_bytes=7)),
        "deliver": AsyncMock(return_value=DeliveryResult(status="confirmed", message_id=9, actual_bytes=7)),
        "status": AsyncMock(),
        "notify_failure": AsyncMock(),
    }
    callbacks.update(overrides)
    return MediaWorkflow(registry, max_file_bytes=MAX_FILE_BYTES, **callbacks)


async def submit(workflow: MediaWorkflow) -> Any:
    return await workflow.submit(user_id=42, chat_id=4200, text=LINK, chat_type="private")


async def select(workflow: MediaWorkflow, request: Any) -> Any:
    return await workflow.select(request_id=request.request_id, user_id=42, chat_id=4200,
        preview_message_id=7, option_id=0)


async def test_success_flow_records_every_stage(trace: Trace, tmp_path: Path) -> None:
    workflow = workflow_for(RequestRegistry(), tmp_path)
    request = await submit(workflow)
    await select(workflow, request)
    entries = trace.entries()
    assert stages(entries, request.request_id) == ["received", "inspection_started",
        "inspection_finished", "selection", "download_started", "download_finished", "send_started"]
    finished = next(entry for entry in entries if entry["stage"] == "download_finished")
    assert finished["outcome"] == "ok"
    assert finished["bytes"] == 7
    selection = next(entry for entry in entries if entry["stage"] == "selection")
    assert selection["option_id"] == 0


def fixture_workflow(registry: RequestRegistry, tmp_path: Path, fixture: str) -> MediaWorkflow:
    """A workflow whose inspection is the normalized yt-dlp fixture and whose download echoes the choice."""
    from openmedia.sources.ytdlp import normalize_info

    info = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    result = normalize_info(info, max_file_bytes=MAX_FILE_BYTES)

    async def download(_request: Any, option: FormatOption) -> DownloadResult:
        path = tmp_path / f"media.{option.extension}"
        path.write_bytes(b"fixture")
        return DownloadResult(path=path, media_id=result.metadata.media_id,
            source_format_id=option.source_format_id, media_type=str(option.media_type),
            extension=option.extension, mime_type=option.mime_type, actual_bytes=7)

    return workflow_for(registry, tmp_path, inspect=AsyncMock(return_value=result), download=download)


def assert_no_link_or_identifier(entry: dict[str, Any], *secrets: str) -> None:
    assert not {"source_url", "chat_id", "user_id", "url", "canonical_url", "media_id"} & set(entry)
    text = json.dumps(entry)
    assert "http" not in text
    for secret in secrets:
        assert secret not in text


async def test_tapped_choice_records_choice_kinds_and_a_manual_selection(trace: Trace, tmp_path: Path) -> None:
    workflow = fixture_workflow(RequestRegistry(), tmp_path, "youtube-video.json")
    request = await workflow.submit(user_id=42, chat_id=4200,
        text="https://www.youtube.com/watch?v=fixtureYT01", chat_type="private")
    await select(workflow, request)
    entries = [entry for entry in trace.entries() if entry.get("request_id") == request.request_id]
    finished = next(entry for entry in entries if entry["stage"] == "inspection_finished")
    assert finished["choices"] == ["video", "silent", "audio"]
    assert finished["options"] > 3  # still the count of native options the source offered
    selection = next(entry for entry in entries if entry["stage"] == "selection")
    assert selection["automatic"] is False
    assert selection["option_id"] == 0
    for entry in (finished, selection):
        assert_no_link_or_identifier(entry, "fixtureYT01", "4200")


async def test_linkedin_single_choice_records_an_automatic_selection(trace: Trace, tmp_path: Path) -> None:
    link = "https://www.linkedin.com/posts/example-author_example-slug-ugcPost-7507745133358940161-abcd"
    workflow = fixture_workflow(RequestRegistry(), tmp_path, "linkedin-video-progressive.json")
    request = await workflow.submit(user_id=42, chat_id=4200, text=link, chat_type="private")
    entries = [entry for entry in trace.entries() if entry.get("request_id") == request.request_id]
    seen = [entry["stage"] for entry in entries]
    assert seen[:5] == ["received", "inspection_started", "inspection_finished", "selection", "download_started"]
    finished = next(entry for entry in entries if entry["stage"] == "inspection_finished")
    assert finished["choices"] == ["video"]
    assert finished["options"] == 2
    selection = next(entry for entry in entries if entry["stage"] == "selection")
    assert selection["automatic"] is True
    assert selection["option_id"] == 0
    for entry in (finished, selection):
        # `platform: "linkedin"` is a required field on every request entry (002 data model),
        # so the check targets the link's host and path fragments, not the platform name.
        assert_no_link_or_identifier(entry, "7507745133358940161", "linkedin.com",
            "example-author", "example-slug", "4200")


async def test_worker_failure_names_stage_cause_chain_and_worker_output(trace: Trace, tmp_path: Path) -> None:
    error = WorkerRemoteError("unavailable", "download")
    error.worker_output = "ERROR: <redacted-url> HTTP Error 403"
    workflow = workflow_for(RequestRegistry(), tmp_path, download=AsyncMock(side_effect=error))
    request = await submit(workflow)
    result = await select(workflow, request)
    assert result.status == "failed"
    entries = trace.entries()
    assert stages(entries, request.request_id)[-2:] == ["download_started", "download_finished"]
    failed = entries[-1]
    assert failed["level"] == "ERROR"
    assert failed["outcome"] == "failed"
    assert failed["failed_stage"] == "downloading"
    assert failed["error_category"] == "unavailable"
    assert failed["worker_output"] == "ERROR: <redacted-url> HTTP Error 403"
    assert "WorkerRemoteError" in failed["error"]


async def test_inspection_timeout_names_the_deadline(trace: Trace, tmp_path: Path) -> None:
    async def slow(*_args: Any) -> None:
        await asyncio.sleep(1)

    workflow = workflow_for(RequestRegistry(), tmp_path, inspect=slow)
    workflow.inspection_seconds = 0.03
    workflow.reap_reserve = 0
    with pytest.raises(TimeoutError):
        await submit(workflow)
    failed = trace.entries()[-1]
    assert failed["stage"] == "inspection_finished"
    assert failed["error_category"] == "timeout"
    assert failed["deadline"] == "inspection"
    assert failed["deadline_seconds"] == 0.03
    assert failed["elapsed_seconds"] >= 0.03


async def test_selection_expiry_is_recorded(trace: Trace, tmp_path: Path) -> None:
    registry = RequestRegistry()
    request = await submit(workflow_for(registry, tmp_path))
    assert await registry.expire_pending(now=request.preview_expires_at + 1) == [request.request_id]
    expired = trace.entries()[-1]
    assert expired["stage"] == "expired"
    assert expired["request_id"] == request.request_id
    assert expired["deadline"] == "selection"
    assert expired["deadline_seconds"] == 900


async def test_refused_admission_is_recorded(trace: Trace, tmp_path: Path) -> None:
    registry = RequestRegistry(max_workers=1)
    gate = asyncio.Event()

    async def held(*_args: Any) -> Any:
        await gate.wait()
        raise WorkerRemoteError("unavailable", "inspection")

    first = asyncio.create_task(workflow_for(registry, tmp_path, inspect=held).submit(
        user_id=1, chat_id=1, text=LINK, chat_type="private"))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    with pytest.raises(Exception):
        await workflow_for(registry, tmp_path).submit(user_id=2, chat_id=2, text=LINK, chat_type="private")
    gate.set()
    with pytest.raises(WorkerRemoteError):
        await first
    rejected = [entry for entry in trace.entries() if entry["stage"] == "rejected"]
    assert [entry["outcome"] for entry in rejected] == ["work_busy"]


async def test_identifiers_appear_once_and_never_on_the_console(
    trace: Trace, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    console = logging.StreamHandler()
    logging.getLogger().addHandler(console)
    try:
        workflow = workflow_for(RequestRegistry(), tmp_path)
        request = await submit(workflow)
        await select(workflow, request)
        entries = trace.entries()
    finally:
        logging.getLogger().removeHandler(console)
    carrying = [entry for entry in entries if {"source_url", "chat_id", "user_id"} & set(entry)]
    assert [entry["stage"] for entry in carrying] == ["received"]
    assert carrying[0]["source_url"] == "https://www.youtube.com/watch?v=abcDEF12345" or MEDIA_ID in carrying[0]["source_url"]
    assert (carrying[0]["chat_id"], carrying[0]["user_id"]) == (4200, 42)
    forbidden = {"username", "first_name", "last_name", "phone", "text"}
    assert not any(forbidden & set(entry) for entry in entries)
    captured = capsys.readouterr()
    assert MEDIA_ID not in captured.err
    assert "source_url" not in captured.err


async def test_failed_worker_carries_its_sanitized_stderr() -> None:
    import sys

    from openmedia.workers import WorkerError, WorkerSupervisor

    script = ("import sys; sys.stderr.write('ERROR: https://cdn.example/v?sig=abc denied\\n'); "
        "sys.stderr.flush(); sys.exit(3)")
    worker = WorkerSupervisor([sys.executable, "-c", script], termination_grace=0.5)
    with pytest.raises(WorkerError) as exc_info:
        await worker.run("inspect", {}, timeout=5)
    output = exc_info.value.worker_output
    assert "denied" in output
    assert "sig=abc" not in output


async def test_runtime_cleanup_is_recorded(trace: Trace, tmp_path: Path) -> None:
    import openmedia.__main__ as runtime
    from openmedia.workers import create_request_directory

    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    callbacks = runtime.RuntimeCallbacks(Settings(telegram_bot_token=TOKEN, work_dir=work), object())
    request = RequestRegistry().new_request(user_id=1, chat_id=1, source_url=LINK,
        platform="youtube", media_id=MEDIA_ID)
    request.work_directory = create_request_directory(work, request.request_id)
    await callbacks.cleanup(request)
    cleanup = trace.entries()[-1]
    assert (cleanup["stage"], cleanup["outcome"]) == ("cleanup", "removed")
    assert cleanup["request_id"] == request.request_id


def lifecycle_settings(directory: Path) -> Settings:
    return Settings(telegram_bot_token=TOKEN, diagnostic_log=True, diagnostic_log_dir=directory)


def test_two_runs_share_one_day_file_with_lifecycle_entries(tmp_path: Path) -> None:
    import openmedia.__main__ as runtime

    directory = tmp_path / "logs"
    runtime.run_with_diagnostics(lifecycle_settings(directory), lambda: None)
    runtime.run_with_diagnostics(lifecycle_settings(directory), lambda: None)
    files = list(directory.iterdir())
    assert len(files) == 1
    text = files[0].read_text()
    entries = [json.loads(line) for line in text.splitlines()]
    assert [entry["stage"] for entry in entries] == ["startup", "shutdown", "startup", "shutdown"]
    assert entries[1]["reason"] == "signal"
    assert entries[0]["origin"] == "lifecycle"
    assert entries[0]["settings"]["max_workers"] == 2
    assert "telegram_bot_token" not in entries[0]["settings"]
    assert TOKEN not in text


def test_a_crash_is_recorded_with_its_error_chain(tmp_path: Path) -> None:
    import openmedia.__main__ as runtime

    def explode() -> None:
        raise RuntimeError("polling died")

    directory = tmp_path / "logs"
    with pytest.raises(RuntimeError):
        runtime.run_with_diagnostics(lifecycle_settings(directory), explode)
    entries = [json.loads(line) for path in directory.iterdir() for line in path.read_text().splitlines()]
    assert [entry["stage"] for entry in entries] == ["startup", "crash", "shutdown"]
    assert entries[1]["level"] == "CRITICAL"
    assert "polling died" in entries[1]["error"]
    assert entries[2]["reason"] == "error"


async def test_an_unwritable_log_never_changes_a_request_outcome(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    async def journey(name: str) -> tuple[str, list[str]]:
        calls: list[str] = []

        async def status(_request: Any, stage: str) -> None:
            calls.append(stage)

        workflow = workflow_for(RequestRegistry(), tmp_path / name, status=status)
        request = await submit(workflow)
        result = await select(workflow, request)
        return str(result.status), calls

    (tmp_path / "baseline").mkdir()
    (tmp_path / "broken").mkdir()
    baseline = await journey("baseline")

    blocker = tmp_path / "not-a-directory"
    blocker.write_text("")
    stop = diagnostics.configure_diagnostics(lifecycle_settings(blocker / "logs"))
    try:
        broken = await journey("broken")
    finally:
        stop()
    assert broken == baseline
    assert capsys.readouterr().err.count("diagnostic log unavailable") == 1


async def test_a_sweep_that_did_work_is_recorded(trace: Trace, tmp_path: Path) -> None:
    import openmedia.__main__ as runtime

    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    callbacks = runtime.RuntimeCallbacks(Settings(telegram_bot_token=TOKEN, work_dir=work), object())
    registry = RequestRegistry()
    request = await submit(workflow_for(registry, tmp_path))
    registry.monotonic = lambda: request.preview_expires_at + 1
    await callbacks.sweep_once(registry)
    await callbacks.sweep_once(registry)  # nothing left to do: no second entry
    sweeps = [entry for entry in trace.entries() if entry["stage"] == "sweep"]
    assert len(sweeps) == 1
    assert sweeps[0]["origin"] == "sweep"
    assert sweeps[0]["expired"] == 1


class TestCommandLineModes:
    def patch(self, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
        import openmedia.__main__ as runtime

        monkeypatch.setattr(runtime.Settings, "from_env", lambda: settings)
        monkeypatch.setattr(runtime.shutil, "which", lambda name: f"/usr/bin/{name}")
        monkeypatch.setattr(runtime, "build_application", lambda settings: pytest.fail("must not poll"))

    def settings(self, tmp_path: Path, directory: Path, *, enabled: bool) -> Settings:
        work = tmp_path / "work"
        return Settings(telegram_bot_token=TOKEN, work_dir=work, diagnostic_log=enabled,
            diagnostic_log_dir=directory)

    def test_flag_off_check_config_creates_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import openmedia.__main__ as runtime

        directory = tmp_path / "logs"
        self.patch(monkeypatch, self.settings(tmp_path, directory, enabled=False))
        assert runtime.main(["--check-config"]) == 0
        assert not directory.exists()
        assert "diagnostic_log=off" in capsys.readouterr().out

    def test_flag_on_check_config_probes_and_leaves_an_empty_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import openmedia.__main__ as runtime

        directory = tmp_path / "logs"
        self.patch(monkeypatch, self.settings(tmp_path, directory, enabled=True))
        assert runtime.main(["--check-config"]) == 0
        assert directory.is_dir()
        assert list(directory.iterdir()) == []
        assert f"diagnostic_log=on ({directory})" in capsys.readouterr().out

    def test_flag_on_unwritable_directory_exits_two_naming_path_and_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import openmedia.__main__ as runtime

        blocker = tmp_path / "file"
        blocker.write_text("")
        directory = blocker / "logs"
        self.patch(monkeypatch, self.settings(tmp_path, directory, enabled=True))
        assert runtime.main(["--check-config"]) == 2
        error = capsys.readouterr().err
        assert "OPENMEDIA_DIAGNOSTIC_LOG_DIR" in error
        assert str(directory) in error
        assert "NotADirectoryError" in error or "Not a directory" in error
        assert TOKEN not in error

    def test_healthcheck_never_touches_the_log_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import openmedia.__main__ as runtime

        directory = tmp_path / "logs"
        self.patch(monkeypatch, self.settings(tmp_path, directory, enabled=True))
        runtime.main(["--healthcheck"])
        assert not directory.exists()


async def test_flag_off_full_flow_leaves_no_files(tmp_path: Path) -> None:
    directory = tmp_path / "logs"
    stop = diagnostics.configure_diagnostics(Settings(telegram_bot_token=TOKEN,
        diagnostic_log=False, diagnostic_log_dir=directory))
    try:
        workflow = workflow_for(RequestRegistry(), tmp_path)
        await select(workflow, await submit(workflow))
    finally:
        stop()
    assert not directory.exists()


@pytest.mark.parametrize(("level", "expected"), [("INFO", ["kept"]), ("DEBUG", ["detail", "kept"])])
def test_detail_level_filters_the_file(tmp_path: Path, level: str, expected: list[str]) -> None:
    stop = diagnostics.configure_diagnostics(Settings(telegram_bot_token=TOKEN, diagnostic_log=True,
        diagnostic_log_dir=tmp_path, diagnostic_log_level=level))
    try:
        diagnostics.event("detail", origin="lifecycle", level=logging.DEBUG)
        diagnostics.event("kept", origin="lifecycle")
    finally:
        stop()
    entries = [json.loads(line) for path in tmp_path.iterdir() for line in path.read_text().splitlines()]
    assert [entry["stage"] for entry in entries] == expected


def test_worker_progress_is_debug_detail_with_nested_redaction(trace: Trace, tmp_path: Path) -> None:
    import openmedia.__main__ as runtime

    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    callbacks = runtime.RuntimeCallbacks(Settings(telegram_bot_token=TOKEN, work_dir=work), object())
    request = RequestRegistry().new_request(user_id=1, chat_id=1, source_url=LINK,
        platform="youtube", media_id=MEDIA_ID)
    callbacks.upstream(request, {"upstream_status_class": "2xx", "url": "https://cdn.example/v?sig=abc"})
    progress = next(entry for entry in trace.entries() if entry["stage"] == "worker_progress")
    assert progress["level"] == "DEBUG"
    assert progress["progress"] == {"upstream_status_class": "2xx", "url": "<redacted-url>"}


@pytest.mark.parametrize("enabled", [False, True])
def test_console_gets_one_start_and_one_stop_line(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, enabled: bool
) -> None:
    import openmedia.__main__ as runtime

    directory = tmp_path / "logs"
    settings = Settings(telegram_bot_token=TOKEN, diagnostic_log=enabled, diagnostic_log_dir=directory)
    with caplog.at_level(logging.INFO, logger="openmedia"):
        runtime.run_with_diagnostics(settings, lambda: None)
    lines = [record.getMessage() for record in caplog.records if record.name == "openmedia"]
    state = f"on, {directory}" if enabled else "off"
    assert lines == [f"openmedia: started (diagnostic_log={state})", "openmedia: stopped (reason=signal)"]
    assert directory.exists() is enabled


async def test_runtime_journey_puts_every_fr002_stage_in_one_trace(
    trace: Trace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 001 stages reach the file through the root logger; prove it end to end (SC-002)."""
    from types import SimpleNamespace

    import openmedia.__main__ as runtime
    from openmedia.workers import create_request_directory

    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    bot = SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=7)))
    callbacks = runtime.RuntimeCallbacks(Settings(telegram_bot_token=TOKEN, work_dir=work),
        SimpleNamespace(bot=bot))

    async def send_card(*_args: Any, **_kwargs: Any) -> tuple[int, bool]:
        return 7, False

    async def deliver_media(*_args: Any, **_kwargs: Any) -> DeliveryResult:
        return DeliveryResult(status="confirmed", message_id=9, actual_bytes=7)

    monkeypatch.setattr(runtime, "send_card", send_card)
    monkeypatch.setattr(runtime, "deliver_media", deliver_media)

    async def download(request: Any, _option: Any) -> DownloadResult:
        # The real download creates the workspace; deliver and cleanup need it to exist.
        request.work_directory = create_request_directory(work, request.request_id)
        path = request.work_directory / "video.mp4"
        path.write_bytes(b"fixture")
        return DownloadResult(path=path, media_id=MEDIA_ID, source_format_id="18",
            media_type="video", extension="mp4", mime_type="video/mp4", actual_bytes=7)

    workflow = workflow_for(RequestRegistry(), tmp_path, status=callbacks.status,
        publish_preview=callbacks.preview, download=download, deliver=callbacks.deliver,
        cleanup=callbacks.cleanup)
    request = await submit(workflow)
    result = await select(workflow, request)
    assert result.status == "confirmed"

    entries = trace.entries()
    seen = stages(entries, request.request_id)
    expected = ["received", "acknowledgment", "inspection_started", "inspection_finished", "preview",
        "selection", "download_started", "download_finished", "send_started", "delivery", "terminal",
        "cleanup"]
    assert [stage for stage in seen if stage in expected] == expected, seen
    by_stage = {entry["stage"]: entry for entry in entries if entry.get("request_id") == request.request_id}
    assert by_stage["delivery"]["outcome"] == "confirmed"
    assert by_stage["terminal"]["outcome"] == "confirmed"
    assert by_stage["cleanup"]["outcome"] == "removed"
    assert all(entry["origin"] == "request" for entry in by_stage.values())
