"""Bounded newline-delimited JSON source-worker supervision."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import re
import signal
import shutil
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from openmedia.models import FormatOption, MediaMetadata
from openmedia.sources import (
    RESOLUTION_FAILURES,
    DownloadInput,
    DownloadResult,
    InspectInput,
    InspectResult,
)


MAX_RESULT_BYTES = 2 * 1024 * 1024
MAX_STDERR_BYTES = 64 * 1024
MAX_PROTOCOL_BYTES = 4 * 1024 * 1024
EXITED_LEADER_DRAIN_SECONDS = 0.25
FIXED_OPERATIONS = frozenset({"inspect", "download"})
_URL_DIAGNOSTIC = re.compile(rb"https?://[^\s]+")
_TOKEN_DIAGNOSTIC = re.compile(
    rb"(?i)(telegram_bot_token\s*=\s*)[^\s]+|\b\d{6,}:[A-Za-z0-9_-]{20,}\b"
)
_FORBIDDEN_KEYS = frozenset(
    {"telegram_bot_token", "bot_token", "telegram_user_id", "user_id", "chat_id"}
)
_REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")


class WorkerError(RuntimeError):
    pass


class WorkerProtocolError(WorkerError):
    pass


class WorkerTimeout(WorkerError):
    pass


class WorkerRemoteError(WorkerError):
    def __init__(
        self, category: str, stage: str | None = None, detail: str | None = None
    ) -> None:
        self.category = category
        self.stage = stage
        # An allowlisted resolution outcome, kept out of the message text on purpose.
        self.detail = detail
        suffix = f" during {stage}" if stage else ""
        super().__init__(f"worker failed: {category}{suffix}")


ProgressCallback = Callable[[dict[str, Any]], Any]
RateRequestCallback = Callable[[dict[str, Any]], Mapping[str, Any] | Awaitable[Mapping[str, Any]]]
EventCallback = Callable[[dict[str, Any]], Any]


def _contains_forbidden_identity(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_identity(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_identity(child) for child in value)
    return False


def create_request_directory(root: Path, request_id: str) -> Path:
    """Create a private scratch directory from a server request ID."""
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("scratch root must be absolute")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved_root = root.resolve(strict=True)
    if resolved_root != root:
        raise ValueError("scratch root cannot be a symlink")
    safe_id = request_id if _REQUEST_ID.fullmatch(request_id) else "request"
    created = Path(tempfile.mkdtemp(prefix=f"{safe_id}-", dir=resolved_root))
    created.chmod(0o700)
    return created


def cleanup_request_directory(path: Path, *, owned_root: Path) -> bool:
    """Remove one direct child workspace without following symlinks."""
    root = Path(owned_root).resolve(strict=True)
    candidate = Path(path)
    try:
        candidate.parent.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("workspace is outside the owned root") from exc
    if candidate.parent.resolve(strict=True) != root:
        raise ValueError("workspace must be a direct child of the owned root")
    try:
        info = candidate.lstat()
    except FileNotFoundError:
        return False
    if candidate.is_symlink() or not candidate.is_dir():
        raise ValueError("workspace must be a non-symlink directory")
    shutil.rmtree(candidate)
    return True


def sweep_work_directories(
    root: Path,
    *,
    older_than: float,
    wall_time: Callable[[], float] = time.time,
) -> list[Path]:
    """Delete stale request workspaces; unrelated root entries are left untouched."""
    root = Path(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved = root.resolve(strict=True)
    if resolved != root or root.is_symlink():
        raise ValueError("workspace root cannot be a symlink")
    removed: list[Path] = []
    for child in root.iterdir():
        if not re.match(r"^[0-9a-f]{32}-", child.name):
            continue
        try:
            info = child.lstat()
        except FileNotFoundError:
            continue
        if child.is_symlink() or not child.is_dir() or wall_time() - info.st_mtime < older_than:
            continue
        try:
            cleanup_request_directory(child, owned_root=root)
            removed.append(child)
        except OSError:
            logging.getLogger("openmedia").warning("workspace cleanup failed; retrying on next sweep")
    return removed


def inspect_payload(request: InspectInput) -> dict[str, Any]:
    return {
        "source_url": request.source_url,
        "request_id": request.request_id,
        "work_directory": str(request.work_directory),
        "deadline": request.deadline,
        "response_limit": request.response_limit,
        "metadata_limit": request.metadata_limit,
        "thumbnail_limit": request.thumbnail_limit,
        "output_limit": request.output_limit,
    }


def download_payload(request: DownloadInput) -> dict[str, Any]:
    return {
        "request_id": request.request_id,
        "metadata": _json_value(request.metadata),
        "option": _json_value(request.option),
        "work_directory": str(request.work_directory),
        "deadline": request.deadline,
        "output_limit": request.output_limit,
        "workspace_limit": request.workspace_limit,
    }


def decode_inspect_result(value: Mapping[str, Any]) -> InspectResult:
    metadata = MediaMetadata(**value["metadata"])
    options = tuple(FormatOption(**item) for item in value["options"])
    thumbnail = value.get("thumbnail_path")
    return InspectResult(metadata, options, Path(thumbnail) if thumbnail else None)


def decode_download_result(value: Mapping[str, Any]) -> DownloadResult:
    return DownloadResult(
        path=Path(value["path"]),
        actual_bytes=int(value["actual_bytes"]),
        media_id=str(value["media_id"]),
        source_format_id=str(value["source_format_id"]),
        media_type=str(value["media_type"]),
        extension=str(value["extension"]),
        mime_type=str(value["mime_type"]),
    )


class WorkerSupervisor:
    """Run one short-lived worker and validate every protocol boundary."""

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        result_limit: int = MAX_RESULT_BYTES,
        stderr_limit: int = MAX_STDERR_BYTES,
        protocol_limit: int = MAX_PROTOCOL_BYTES,
        progress_limit: int = 600,
        termination_grace: float = 5.0,
    ) -> None:
        if isinstance(command, (str, bytes)):
            raise TypeError("worker command must be an argument array")
        self.command = tuple(command or (sys.executable, "-m", "openmedia.workers", "--child"))
        if not self.command or any(not isinstance(item, str) or not item for item in self.command):
            raise ValueError("worker command must contain nonempty arguments")
        if min(result_limit, stderr_limit, protocol_limit, progress_limit) <= 0:
            raise ValueError("worker protocol limits must be positive")
        if protocol_limit < result_limit:
            raise ValueError("protocol_limit cannot be smaller than result_limit")
        if termination_grace <= 0 or termination_grace > 5:
            raise ValueError("termination_grace must be in (0, 5]")
        self.result_limit = result_limit
        self.stderr_limit = stderr_limit
        self.protocol_limit = protocol_limit
        self.progress_limit = progress_limit
        self.termination_grace = termination_grace
        self.last_stderr = b""
        self._active: set[asyncio.subprocess.Process] = set()

    @property
    def active_count(self) -> int:
        return len(self._active)

    def kill_active(self) -> None:
        """Shutdown backstop: SIGKILL every running group without awaiting its owner task."""
        for process in tuple(self._active):
            self._signal_group(process, signal.SIGKILL)

    async def run(
        self,
        operation: str,
        payload: Mapping[str, Any],
        *,
        timeout: float,
        on_progress: ProgressCallback | None = None,
        on_rate_request: RateRequestCallback | None = None,
        on_rate_limited: EventCallback | None = None,
    ) -> Any:
        if operation not in FIXED_OPERATIONS:
            raise ValueError("worker operation must be inspect or download")
        if timeout <= 0:
            raise ValueError("worker timeout must be positive")
        if _contains_forbidden_identity(payload):
            raise ValueError("worker payload cannot contain bot tokens or Telegram identities")
        message = dict(payload)
        message["operation"] = operation
        encoded = json.dumps(message, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
        if len(encoded) > self.result_limit:
            raise WorkerProtocolError("worker input exceeds the protocol limit")

        process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._minimal_environment(Path(str(payload["work_directory"])) if "work_directory" in payload else None),
            start_new_session=True,
            limit=self.result_limit + 1024,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        stderr_task = asyncio.create_task(self._read_stderr(process.stderr))
        self._active.add(process)
        try:
            process.stdin.write(encoded)
            await process.stdin.drain()
            operation_budget = (
                timeout - self.termination_grace
                if timeout > self.termination_grace
                else timeout
            )
            try:
                async with asyncio.timeout(operation_budget):
                    result = await self._read_protocol(
                        process,
                        on_progress=on_progress,
                        on_rate_request=on_rate_request,
                        on_rate_limited=on_rate_limited,
                    )
            except TimeoutError as exc:
                await self._terminate(process)
                raise WorkerTimeout(f"{operation} worker exceeded its deadline") from exc
            return result
        except BaseException:
            await self._terminate(process)
            raise
        finally:
            self._signal_group(process, signal.SIGKILL)
            self._active.discard(process)
            if process.stdin is not None and not process.stdin.is_closing():
                process.stdin.close()
            try:
                self.last_stderr = await asyncio.wait_for(stderr_task, timeout=self.termination_grace)
            except BaseException:
                stderr_task.cancel()
                self.last_stderr = b""
            # last_stderr is shared by concurrent workers, so the sanitized capture travels on
            # the failure itself for the diagnostic log (002 research §7).
            failure = sys.exc_info()[1]
            if failure is not None and self.last_stderr:
                failure.worker_output = self.last_stderr.decode("utf-8", errors="replace")  # type: ignore[attr-defined]

    async def _read_protocol(
        self,
        process: asyncio.subprocess.Process,
        *,
        on_progress: ProgressCallback | None,
        on_rate_request: RateRequestCallback | None,
        on_rate_limited: EventCallback | None,
    ) -> Any:
        assert process.stdout is not None
        total_bytes = 0
        terminal: tuple[str, dict[str, Any]] | None = None
        progress_count = 0
        exited = asyncio.ensure_future(process.wait())
        while True:
            read = asyncio.ensure_future(process.stdout.readline())
            try:
                await asyncio.wait({read, exited}, return_when=asyncio.FIRST_COMPLETED)
                if not read.done():
                    # The leader is gone; a descendant holding the pipe must not stall EOF.
                    await asyncio.wait({read}, timeout=EXITED_LEADER_DRAIN_SECONDS)
                if not read.done():
                    break
                line = read.result()
            except (ValueError, asyncio.LimitOverrunError) as exc:
                raise WorkerProtocolError("worker emitted an oversized event") from exc
            finally:
                if not read.done():
                    read.cancel()
            if not line:
                break
            total_bytes += len(line)
            if total_bytes > self.protocol_limit:
                raise WorkerProtocolError("worker emitted too much protocol output")
            if len(line) > self.result_limit:
                raise WorkerProtocolError("worker event exceeds the 2 MiB result limit")
            try:
                event = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise WorkerProtocolError("worker emitted malformed JSON") from exc
            if not isinstance(event, dict) or not isinstance(event.get("event"), str):
                raise WorkerProtocolError("worker event has an invalid shape")
            event_type = event["event"]
            if event_type in ("result", "error"):
                if terminal is not None:
                    raise WorkerProtocolError("worker emitted multiple terminal events")
                terminal = (event_type, event)
            elif event_type == "progress":
                progress_count += 1
                if progress_count <= self.progress_limit and on_progress is not None:
                    produced = on_progress(event)
                    if inspect.isawaitable(produced):
                        await produced
            elif event_type == "rate_limited":
                if on_rate_limited is not None:
                    produced = on_rate_limited(event)
                    if inspect.isawaitable(produced):
                        await produced
            elif event_type == "rate_request":
                if on_rate_request is None:
                    reply: Mapping[str, Any] = {"allowed": False, "delay": 0}
                else:
                    produced = on_rate_request(event)
                    reply = await produced if inspect.isawaitable(produced) else produced
                await self._send_rate_reply(process, reply)
            else:
                raise WorkerProtocolError(f"unknown worker event: {event_type}")

        return_code = await exited
        if terminal is None:
            raise WorkerProtocolError(
                f"worker exited with status {return_code} without a terminal event"
            )
        event_type, event = terminal
        if event_type == "error":
            category = event.get("category")
            if not isinstance(category, str):
                raise WorkerProtocolError("worker error omitted its category")
            stage = event.get("stage")
            detail = event.get("detail")
            raise WorkerRemoteError(
                category,
                stage if isinstance(stage, str) else None,
                detail if isinstance(detail, str) and detail in RESOLUTION_FAILURES else None,
            )
        if return_code != 0:
            raise WorkerProtocolError(
                f"worker returned a result but exited with status {return_code}"
            )
        return event.get("value")

    async def _send_rate_reply(
        self, process: asyncio.subprocess.Process, reply: Mapping[str, Any]
    ) -> None:
        if process.stdin is None or process.stdin.is_closing():
            raise WorkerProtocolError("worker requested rate control after closing input")
        event = {"event": "rate_reply", **dict(reply)}
        encoded = json.dumps(event, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(encoded) > 4096:
            raise WorkerProtocolError("rate-control reply is oversized")
        process.stdin.write(encoded)
        await process.stdin.drain()

    async def _read_stderr(self, stream: asyncio.StreamReader) -> bytes:
        captured = bytearray()
        while chunk := await stream.read(8192):
            remaining = self.stderr_limit - len(captured)
            if remaining > 0:
                captured.extend(chunk[:remaining])
        sanitized = _URL_DIAGNOSTIC.sub(b"<redacted-url>", bytes(captured))
        sanitized = _TOKEN_DIAGNOSTIC.sub(
            lambda match: (
                match.group(1) + b"<redacted>" if match.group(1) else b"<redacted-token>"
            ),
            sanitized,
        )
        return sanitized

    async def _terminate(self, process: asyncio.subprocess.Process) -> None:
        self._signal_group(process, signal.SIGTERM)
        try:
            await asyncio.wait_for(process.wait(), timeout=self.termination_grace)
        except TimeoutError:
            pass
        finally:
            # A reaped leader does not imply its process group is empty.
            self._signal_group(process, signal.SIGKILL)
            await process.wait()

    @staticmethod
    def _signal_group(process: asyncio.subprocess.Process, signum: signal.Signals) -> None:
        try:
            os.killpg(process.pid, signum)
        except (AttributeError, ProcessLookupError):
            try:
                process.send_signal(signum)
            except ProcessLookupError:
                pass

    @staticmethod
    def _minimal_environment(work_directory: Path | None = None) -> dict[str, str]:
        environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
        }
        if work_directory is not None:
            environment.update(DENO_DIR=str(work_directory / "deno"), TMPDIR=str(work_directory),
                DENO_NO_UPDATE_CHECK="1", DENO_NO_PROMPT="1")
        if os.name == "nt" and "SYSTEMROOT" in os.environ:
            environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        return environment


def _child_main() -> int:
    """Run one fixed adapter operation using only guarded worker capabilities."""
    try:
        message = json.loads(sys.stdin.readline())
        operation = message.get("operation")
        if operation not in FIXED_OPERATIONS:
            raise ValueError("unsupported operation")
        from openmedia.network import GuardedHTTPTransport, guard_public_sockets
        from openmedia.sources import (
            SourceAdapterError,
            SourceRouter,
            fetch_optional_thumbnail,
        )

        class ProtocolRateControl:
            def observe(self, platform: str, status: int | None) -> None:
                status_class = "connection_failure" if status is None else ("429" if status == 429 else f"{status // 100}xx")
                print(json.dumps({"event": "progress", "upstream_status_class": status_class}), flush=True)

            def acquire(self, platform: str, request_class: str, *, deadline: float) -> float:
                print(
                    json.dumps(
                        {
                            "event": "rate_request",
                            "platform": platform,
                            "request_class": request_class,
                            "deadline": deadline,
                        }
                    ),
                    flush=True,
                )
                reply = json.loads(sys.stdin.readline())
                if reply.get("event") != "rate_reply" or not reply.get("allowed"):
                    raise SourceAdapterError("rate_limited", stage=operation)
                delay = float(reply.get("delay", 0))
                if delay < 0 or time.monotonic() + delay >= deadline:
                    raise SourceAdapterError("rate_limited", stage=operation)
                if delay:
                    time.sleep(delay)
                return delay

            def limited(self, platform: str, request_class: str, *, retry_after: float | None) -> None:
                print(
                    json.dumps(
                        {
                            "event": "rate_limited",
                            "platform": platform,
                            "request_class": request_class,
                            "retry_after": retry_after,
                        }
                    ),
                    flush=True,
                )

        rate = ProtocolRateControl()
        transport = GuardedHTTPTransport()
        router = SourceRouter()
        def bind_transport(platform, request, request_class):
            transport.on_request = lambda: rate.acquire(platform, request_class, deadline=request.deadline)
            def response(status, headers):
                rate.observe(platform, status)
                if status == 429:
                    raw = headers.get("retry-after", "")
                    retry = float(raw) if raw.isdigit() else None
                    rate.limited(platform, request_class, retry_after=retry)
                    raise SourceAdapterError("rate_limited", stage=operation)
            transport.on_response = response
        # Backstop for any library request path that bypasses the patched metadata clients.
        with guard_public_sockets(transport.policy):
            if operation == "inspect":
                request = InspectInput(
                    source_url=message["source_url"],
                    request_id=message["request_id"],
                    work_directory=Path(message["work_directory"]),
                    deadline=float(message["deadline"]),
                    response_limit=int(message.get("response_limit", 2 * 1024 * 1024)),
                    metadata_limit=int(message.get("metadata_limit", 8 * 1024 * 1024)),
                    thumbnail_limit=int(message.get("thumbnail_limit", 1024 * 1024)),
                    output_limit=int(message.get("output_limit", 50_000_000)),
                )
                from openmedia.sources import recognize_source_url
                bind_transport(recognize_source_url(request.source_url).platform, request, "metadata")
                result = router.inspect(request, transport=transport, rate_control=rate)
                result = fetch_optional_thumbnail(result, request, transport=transport)
            else:
                metadata = MediaMetadata(**message["metadata"])
                option = FormatOption(**message["option"])
                request = DownloadInput(
                    request_id=message["request_id"],
                    metadata=metadata,
                    option=option,
                    work_directory=Path(message["work_directory"]),
                    deadline=float(message["deadline"]),
                    output_limit=int(message["output_limit"]),
                    workspace_limit=int(message["workspace_limit"]),
                )
                bind_transport(metadata.platform, request, "media")
                result = router.download(request, transport=transport, rate_control=rate)
        print(json.dumps({"event": "result", "value": _json_value(result)}), flush=True)
        return 0
    except Exception as exc:
        from openmedia.network import ResponseTooLarge, UnsafeDestination
        category = getattr(getattr(exc, "category", None), "value", None) or "internal"
        if isinstance(exc, ResponseTooLarge):
            category = "too_large"
        elif isinstance(exc, UnsafeDestination):
            category = "unsafe_destination"
        elif isinstance(exc, OSError) and exc.errno == 28:
            category = "storage_exhausted"
        elif isinstance(exc, (ConnectionError, TimeoutError)) and category == "internal":
            # A dropped or stalled upstream connection is retryable, not a fault in the service.
            category = "timeout"
        if isinstance(exc, (ConnectionError, TimeoutError)):
            print(json.dumps({"event": "progress", "upstream_status_class": "connection_failure"}), flush=True)
        stage = getattr(exc, "stage", None)
        error_event = {"event": "error", "category": category, "stage": stage}
        detail = getattr(exc, "detail", None)
        if isinstance(detail, str) and detail in RESOLUTION_FAILURES:
            error_event["detail"] = detail
        print(json.dumps(error_event), flush=True)
        return 1


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return {item.name: _json_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(child) for child in value]
    return value


if __name__ == "__main__":
    if sys.argv[1:] == ["--child"]:
        raise SystemExit(_child_main())
    raise SystemExit("workers.py is an internal module")
