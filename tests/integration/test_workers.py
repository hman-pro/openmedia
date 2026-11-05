from __future__ import annotations


def test_worker_environment_keeps_trusted_tools_and_private_scratch(tmp_path):
    from openmedia.workers import WorkerSupervisor
    environment = WorkerSupervisor._minimal_environment(tmp_path)
    assert "/usr/local/bin" in environment["PATH"].split(":")
    assert environment["DENO_DIR"] == str(tmp_path / "deno")
    assert "TELEGRAM_BOT_TOKEN" not in environment

import os
import sys
from pathlib import Path

import pytest

from openmedia.workers import WorkerProtocolError, WorkerSupervisor, WorkerTimeout


STUB = Path(__file__).parents[1] / "fixtures" / "worker_stub.py"


def supervisor(**kwargs: object) -> WorkerSupervisor:
    return WorkerSupervisor([sys.executable, str(STUB)], **kwargs)


@pytest.mark.parametrize("operation", ["inspect", "download"])
async def test_fixed_operations_are_dispatched(operation: str) -> None:
    result = await supervisor().run(operation, {}, timeout=1)
    assert result == {"operation": operation}


async def test_arbitrary_operation_is_rejected_before_spawn() -> None:
    with pytest.raises(ValueError, match="operation"):
        await supervisor().run("shell", {}, timeout=1)


async def test_worker_environment_is_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setenv("OPENMEDIA_USER_ID", "123")
    result = await supervisor().run("inspect", {"mode": "environment"}, timeout=1)
    assert result["token"] is None
    assert result["user"] is None
    # macOS injects __CF_USER_TEXT_ENCODING into child processes even when env is explicit.
    assert set(result["keys"]) <= {
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PYTHONIOENCODING",
        "__CF_USER_TEXT_ENCODING",
    }


@pytest.mark.parametrize("mode", ["malformed", "multiple", "oversized"])
async def test_protocol_violations_fail(mode: str) -> None:
    with pytest.raises(WorkerProtocolError):
        await supervisor().run("inspect", {"mode": mode}, timeout=1)


async def test_stderr_and_progress_are_bounded() -> None:
    noisy_stderr = supervisor(stderr_limit=1024)
    assert await noisy_stderr.run("inspect", {"mode": "stderr"}, timeout=1) is True
    assert len(noisy_stderr.last_stderr) == 1024

    progress: list[dict[str, object]] = []
    noisy_progress = supervisor(progress_limit=5)
    assert await noisy_progress.run(
        "download", {"mode": "progress"}, timeout=1, on_progress=progress.append
    ) is True
    assert len(progress) == 5


async def test_parent_answers_rate_control_events() -> None:
    limited: list[dict[str, object]] = []
    result = await supervisor().run(
        "inspect",
        {"mode": "rate"},
        timeout=1,
        on_rate_request=lambda event: {"allowed": True, "delay": 0.25},
        on_rate_limited=limited.append,
    )
    assert result == {"event": "rate_reply", "allowed": True, "delay": 0.25}
    assert limited[0]["retry_after"] == 2


async def test_timeout_kills_and_reaps_before_return(tmp_path: Path) -> None:
    marker = tmp_path / "late-write"
    with pytest.raises(WorkerTimeout):
        await supervisor(termination_grace=0.05).run(
            "download", {"mode": "hang", "marker": str(marker)}, timeout=0.05
        )
    await __import__("asyncio").sleep(0.1)
    assert not marker.exists()


async def test_kill_active_ends_every_running_worker_group() -> None:
    import asyncio

    worker = WorkerSupervisor([sys.executable, "-c", "import time; time.sleep(60)"], termination_grace=0.2)
    job = asyncio.create_task(worker.run("inspect", {}, timeout=60))
    for _ in range(100):
        if worker.active_count:
            break
        await asyncio.sleep(0.02)
    assert worker.active_count == 1

    worker.kill_active()

    with pytest.raises(WorkerProtocolError):
        await asyncio.wait_for(job, 2)
    assert worker.active_count == 0


def _error_event_worker(event: dict[str, object]) -> WorkerSupervisor:
    """Worker that reads one message and prints exactly the given error event."""
    import json

    script = (
        "import sys; sys.stdin.readline(); "
        f"print({json.dumps(json.dumps(event))}, flush=True)"
    )
    return WorkerSupervisor([sys.executable, "-c", script])


async def test_remote_error_carries_allowlisted_resolution_detail() -> None:
    from openmedia.workers import WorkerRemoteError

    worker = _error_event_worker(
        {
            "event": "error",
            "category": "short_link_unresolved",
            "stage": "inspection",
            "detail": "not_found",
        }
    )
    with pytest.raises(WorkerRemoteError) as caught:
        await worker.run("inspect", {"mode": "error_detail"}, timeout=5)
    assert caught.value.category == "short_link_unresolved"
    assert caught.value.stage == "inspection"
    assert caught.value.detail == "not_found"
    assert "not_found" not in str(caught.value)


async def test_remote_error_drops_detail_outside_allowlist() -> None:
    from openmedia.workers import WorkerRemoteError

    worker = _error_event_worker(
        {
            "event": "error",
            "category": "short_link_unresolved",
            "stage": "inspection",
            "detail": "https://evil.example/",
        }
    )
    with pytest.raises(WorkerRemoteError) as caught:
        await worker.run("inspect", {"mode": "error_bad_detail"}, timeout=5)
    assert caught.value.category == "short_link_unresolved"
    assert caught.value.detail is None
    assert "evil.example" not in str(caught.value)


async def test_remote_error_without_detail_has_none() -> None:
    from openmedia.workers import WorkerRemoteError

    with pytest.raises(WorkerRemoteError) as caught:
        await supervisor().run("inspect", {"mode": "unknown"}, timeout=5)
    assert caught.value.category == "internal"
    assert caught.value.detail is None


def test_download_result_measured_metadata_survives_the_worker_boundary(tmp_path: Path) -> None:
    from openmedia.sources import DownloadResult
    from openmedia.workers import _json_value, decode_download_result

    result = DownloadResult(tmp_path / "selected.mp4", 7, "id", "1", "video", "mp4", "video/mp4",
        width=720, height=1280, duration_seconds=209.789)
    assert decode_download_result(_json_value(result)) == result
    # Image adapters report no measured video metadata.
    bare = DownloadResult(tmp_path / "selected.jpg", 7, "id", "1", "image", "jpg", "image/jpeg")
    assert decode_download_result(_json_value(bare)) == bare


@pytest.mark.parametrize(("category", "stage"), [
    ("music_collection", "input"), ("no_native_audio", "inspection"),
])
async def test_music_errors_survive_worker_protocol(category: str, stage: str) -> None:
    from openmedia.sources import SourceAdapterError
    from openmedia.workers import WorkerRemoteError

    worker = _error_event_worker({"event": "error", "category": category, "stage": stage})
    with pytest.raises(WorkerRemoteError) as caught:
        await worker.run("inspect", {}, timeout=5)
    error = SourceAdapterError(caught.value.category, stage=caught.value.stage)
    assert error.category.value == category
    assert error.stage == stage


async def test_audio_inspection_survives_bounded_worker_protocol() -> None:
    import json
    from openmedia.models import FormatOption, MediaKind, MediaMetadata
    from openmedia.sources import InspectResult
    from openmedia.workers import _json_value, decode_inspect_result

    expected = InspectResult(MediaMetadata(
        platform="youtube", canonical_url="https://music.youtube.com/watch?v=abcDEF12345",
        media_id="abcDEF12345", media_kind="audio",
    ), (FormatOption(option_id=0, adapter="yt_dlp", source_format_id="140",
        media_type="audio", extension="m4a", mime_type="audio/mp4"),))
    event = {"event": "result", "value": _json_value(expected)}
    script = "import sys; sys.stdin.readline(); " + f"print({json.dumps(json.dumps(event))}, flush=True)"
    worker = WorkerSupervisor([sys.executable, "-c", script])
    decoded = decode_inspect_result(await worker.run("inspect", {}, timeout=5))
    assert decoded == expected
    assert decoded.metadata.media_kind is MediaKind.AUDIO
    assert decoded.metadata.canonical_url == expected.metadata.canonical_url
    with pytest.raises(WorkerProtocolError):
        await WorkerSupervisor([sys.executable, "-c", script], result_limit=32).run("inspect", {}, timeout=5)


async def test_file_token_never_enters_worker_environment_or_payload(tmp_path, monkeypatch):
    import json
    from openmedia.config import Settings
    token = '123456789:sentinel-file-loaded-secret'
    path = tmp_path / 'sentinel-credential-path'
    path.write_text(token)
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN_FILE', str(path))
    settings = Settings.from_env()
    script = "import os,sys,json; print(json.dumps({'event':'result','value':{'env':dict(os.environ),'payload':json.loads(sys.stdin.readline())}}))"
    worker = WorkerSupervisor([sys.executable, '-c', script])
    from openmedia.models import FormatOption, MediaMetadata
    from openmedia.sources import InspectInput, DownloadInput
    from openmedia.workers import inspect_payload, download_payload
    metadata = MediaMetadata('youtube', 'https://youtu.be/abcDEF12345', 'abcDEF12345')
    option = FormatOption(0, 'yt_dlp', 'v', 'video', 'mp4', 'video/mp4', includes_audio=False)
    payloads = [inspect_payload(InspectInput(metadata.canonical_url, 'a' * 32, tmp_path, 1000.)),
        download_payload(DownloadInput('a' * 32, metadata, option, tmp_path, 1000., 1000, 2000))]
    rendered = repr(settings)
    for operation, payload in zip(('inspect', 'download'), payloads):
        rendered += json.dumps(await worker.run(operation, payload, timeout=5))
    assert token not in rendered and str(path) not in rendered
    assert 'TELEGRAM_BOT_TOKEN' not in rendered


@pytest.mark.parametrize('key', ['TELEGRAM_BOT_TOKEN_FILE', 'telegram_bot_token_file'])
async def test_file_token_input_is_rejected_before_worker_spawn(key):
    with pytest.raises(ValueError, match='cannot contain bot tokens'):
        await supervisor().run('inspect', {'nested': {key: '/private/file'}}, timeout=1)
