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
