"""Development-only diagnostic log: one JSON Lines file per UTC day, behind a feature flag.

Submitted links and Telegram identifiers are emitted only through the ``openmedia.diagnostic``
logger. It never propagates, so no console handler can see those records, and until
``configure_diagnostics`` turns the flag on it is disabled outright.
"""

from __future__ import annotations

import copy
import json
import logging
import logging.handlers
import os
import queue
import re
import sys
import time
import traceback
from collections.abc import Callable
from contextvars import ContextVar
from datetime import date, datetime, timezone
from pathlib import Path
from typing import IO, Any

from openmedia.config import (
    DIAGNOSTIC_ENTRY_MAX_BYTES,
    DIAGNOSTIC_LOG_MAX_BYTES,
    DIAGNOSTIC_LOG_MAX_DAYS,
    DIAGNOSTIC_QUEUE_RECORDS,
    DIAGNOSTIC_REOPEN_SECONDS,
    Settings,
)


LOGGER_NAME = "openmedia.diagnostic"
REQUEST_CONTEXT: ContextVar[str | None] = ContextVar("request_id", default=None)
QUIET_LIBRARIES = ("httpx", "httpcore", "telegram", "urllib3", "requests")

_URL = re.compile(r"https?://[^\s\"'<>]+")
_TOKEN = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]+")
_DAY_FILE = re.compile(r"openmedia-(\d{4}-\d{2}-\d{2})\.log")
_DISABLED = logging.CRITICAL + 1
_TRUNCATION_MARK = "…[truncated]"
# Cut order when an entry is too large (FR-017): the bulkiest diagnostic text goes first.
_CUT_ORDER = ("error", "worker_output", "msg")
_CORE_KEYS = ("ts", "level", "origin", "stage", "request_id", "truncated")
# Entry keys after ts/level/origin/stage, in file order (data-model.md). Unknown keys follow.
_FIELD_ORDER = (
    "request_id", "msg", "platform", "elapsed_seconds", "source_url", "chat_id", "user_id",
    "option_id", "outcome", "error_category", "failed_stage", "deadline", "deadline_seconds",
    "error", "worker_output", "bytes",
)
# The submitted link is the one URL the file may hold; every other string is fully redacted.
_KEEPS_URL = frozenset({"source_url"})

_logger = logging.getLogger(LOGGER_NAME)
_logger.propagate = False
_logger.addHandler(logging.NullHandler())
_logger.setLevel(_DISABLED)


def redact_secrets(text: str, secrets: tuple[str, ...]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    return _TOKEN.sub("<redacted-token>", text)


def redact(text: str, secrets: tuple[str, ...]) -> str:
    """Console redaction: known secrets, then every URL, then anything token-shaped."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    return _TOKEN.sub("<redacted-token>", _URL.sub("<redacted-url>", text))


def _json_object(message: str) -> dict[str, Any] | None:
    if not message.startswith("{"):
        return None
    try:
        value = json.loads(message)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


class JsonLineFormatter(logging.Formatter):
    """Render one record as one redacted JSON line."""

    def __init__(
        self, *, secrets: tuple[str, ...] = (), max_bytes: int = DIAGNOSTIC_ENTRY_MAX_BYTES
    ) -> None:
        super().__init__()
        self.secrets = secrets
        self.max_bytes = max_bytes

    def entry(self, record: logging.LogRecord) -> dict[str, Any]:
        fields = dict(getattr(record, "diagnostic", None) or {})
        if not fields:
            message = record.getMessage()
            # Feature 001's console events are already JSON objects; lift them into fields.
            fields = _json_object(message) or {"msg": message}
        request_id = (fields.pop("request_id", None)
            or getattr(record, "diagnostic_request_id", None) or REQUEST_CONTEXT.get())
        if request_id is not None:
            fields["request_id"] = request_id
        error = getattr(record, "diagnostic_error", None)
        if error is None and record.exc_info and record.exc_info[0] is not None:
            error = "".join(traceback.format_exception(*record.exc_info))
        if error:
            fields["error"] = error
        dropped = getattr(record, "diagnostic_dropped", 0)
        if dropped:
            fields["dropped"] = dropped

        default_origin = "request" if "stage" in fields and request_id else "library"
        stamp = datetime.fromtimestamp(record.created, timezone.utc)
        entry: dict[str, Any] = {
            "ts": stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "origin": fields.pop("origin", default_origin),
            "stage": fields.pop("stage", record.name),
        }
        for key in (*_FIELD_ORDER, *(key for key in fields if key not in _FIELD_ORDER)):
            value = fields.get(key)
            if value is None:
                continue
            entry[key] = self._clean(value, redact_secrets if key in _KEEPS_URL else redact)
        return entry

    def _clean(self, value: Any, clean: Callable[[str, tuple[str, ...]], str]) -> Any:
        if isinstance(value, str):
            return clean(value, self.secrets)
        if isinstance(value, dict):
            return {str(key): self._clean(item, clean) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._clean(item, clean) for item in value]
        return value

    @staticmethod
    def _dump(entry: dict[str, Any]) -> str:
        return json.dumps(entry, separators=(",", ":"), ensure_ascii=False, default=str)

    def format(self, record: logging.LogRecord) -> str:
        entry = self.entry(record)
        line = self._dump(entry)
        budget = self.max_bytes - 1  # the newline
        if len(line.encode("utf-8")) <= budget:
            return line
        entry["truncated"] = True
        for key in _CUT_ORDER:
            value = entry.get(key)
            if not isinstance(value, str):
                continue
            # Every character is at least one encoded byte, so cutting `excess` characters
            # always frees at least `excess` bytes.
            excess = len(self._dump(entry).encode("utf-8")) - budget + len(_TRUNCATION_MARK.encode("utf-8"))
            entry[key] = value[: max(0, len(value) - excess)] + _TRUNCATION_MARK
            line = self._dump(entry)
            if len(line.encode("utf-8")) <= budget:
                return line
        return self._dump({key: entry[key] for key in _CORE_KEYS if key in entry})


def apply_retention(
    directory: Path,
    today: str,
    *,
    max_days: int = DIAGNOSTIC_LOG_MAX_DAYS,
    max_bytes: int = DIAGNOSTIC_LOG_MAX_BYTES,
    reserve: int | None = None,
) -> int:
    """Remove whole day files, oldest first; return the bytes still held by other days.

    Only ``openmedia-YYYY-MM-DD.log`` names with a real date are considered, so a wrong
    directory setting cannot delete anything else. Age comes from the name, never mtime.
    Today's file is never removed; ``reserve`` is the room it needs (its current size when
    not given).
    """
    current = date.fromisoformat(today)
    others: list[tuple[date, Path, int]] = []
    try:
        candidates = list(Path(directory).iterdir())
    except OSError:
        return 0
    for path in candidates:
        match = _DAY_FILE.fullmatch(path.name)
        if match is None or match.group(1) == today or path.is_symlink() or not path.is_file():
            continue
        try:
            others.append((date.fromisoformat(match.group(1)), path, path.stat().st_size))
        except (ValueError, OSError):
            continue
    if reserve is None:
        try:
            reserve = (Path(directory) / f"openmedia-{today}.log").stat().st_size
        except OSError:
            reserve = 0
    others.sort()
    held = sum(size for _day, _path, size in others)
    for day, path, size in others:
        if (current - day).days < max_days and held + reserve <= max_bytes:
            continue
        try:
            path.unlink()
            held -= size
        except OSError:
            continue
    return held


class DailyFileHandler(logging.Handler):
    """Append each record to ``openmedia-YYYY-MM-DD.log`` for the record's own UTC date.

    States (data-model.md): closed, open(day), paused(day) when today's file alone reaches the
    storage limit, and degraded after a write or open failure. No state ever raises into the
    caller: a log problem must not change a request's outcome (FR-011).
    """

    def __init__(
        self,
        directory: Path,
        *,
        clock: Callable[[], float] = time.time,
        max_bytes: int = DIAGNOSTIC_LOG_MAX_BYTES,
        max_days: int = DIAGNOSTIC_LOG_MAX_DAYS,
        reopen_seconds: float = DIAGNOSTIC_REOPEN_SECONDS,
    ) -> None:
        super().__init__()
        self.directory = Path(directory)
        self.clock = clock
        self.max_bytes = max_bytes
        self.max_days = max_days
        self.reopen_seconds = reopen_seconds
        self._day: str | None = None
        self._stream: IO[str] | None = None
        self._size = 0
        self._other_bytes = 0
        self._paused_day: str | None = None
        self._retry_at: float | None = None  # not None means degraded
        self._lost = 0

    @staticmethod
    def day_of(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")

    def path_for(self, day: str) -> Path:
        return self.directory / f"openmedia-{day}.log"

    def _retain(self, day: str, reserve: int = 0) -> None:
        self._other_bytes = apply_retention(self.directory, day, max_days=self.max_days,
            max_bytes=self.max_bytes, reserve=reserve)

    def _open(self, day: str) -> IO[str]:
        self._close_stream()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.path_for(day)
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        stream = os.fdopen(descriptor, "a", encoding="utf-8")
        self._stream, self._day = stream, day
        self._size = path.stat().st_size
        if self._size:
            # A killed process can leave a torn last line; keep it from swallowing the next entry.
            with path.open("rb") as existing:
                existing.seek(-1, os.SEEK_END)
                if existing.read(1) != b"\n":
                    stream.write("\n")
                    stream.flush()
                    self._size += 1
        self._retain(day, reserve=self._size)
        return stream

    def _close_stream(self) -> None:
        stream, self._stream, self._day = self._stream, None, None
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass

    def _write(self, record: logging.LogRecord) -> None:
        day = self.day_of(record.created)
        if day == self._paused_day:
            return
        stream = self._stream if self._stream is not None and day == self._day else self._open(day)
        data = self.format(record) + "\n"
        needed = len(data.encode("utf-8"))
        if self._other_bytes + self._size + needed > self.max_bytes:
            self._retain(day, reserve=self._size + needed)
            if self._other_bytes + self._size + needed > self.max_bytes:
                self._paused_day = day
                print("openmedia: diagnostic log reached its size limit; paused until the next UTC day",
                    file=sys.stderr)
                return
        stream.write(data)
        stream.flush()
        self._size += needed

    def _recovered(self, record: logging.LogRecord) -> logging.LogRecord:
        notice = logging.LogRecord(LOGGER_NAME, logging.WARNING, __file__, 0, "log_recovered", None, None)
        notice.created = record.created
        notice.diagnostic = {"origin": "lifecycle", "stage": "log_recovered", "lost": self._lost}
        return notice

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self._retry_at is not None:
                if self.clock() < self._retry_at:
                    self._lost += 1
                    return
                self._write(self._recovered(record))
                self._retry_at, self._lost = None, 0
                print("openmedia: diagnostic log recovered", file=sys.stderr)
            self._write(record)
        except Exception as exc:
            self._close_stream()
            self._lost += 1
            if self._retry_at is None:
                # One line per outage, never one per entry, and never a traceback with paths.
                print(f"openmedia: diagnostic log unavailable ({type(exc).__name__}); requests continue",
                    file=sys.stderr)
            self._retry_at = self.clock() + self.reopen_seconds

    def close(self) -> None:
        with self.lock:  # type: ignore[union-attr]
            self._close_stream()
        super().close()


class DroppingQueueHandler(logging.handlers.QueueHandler):
    """Hand records to the writer thread without ever blocking the event loop."""

    def __init__(self, target: queue.Queue[logging.LogRecord]) -> None:
        super().__init__(target)
        self.dropped = 0

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        # Everything tied to the emitting context is resolved here, not on the writer thread:
        # the request ContextVar and the live traceback objects.
        prepared = copy.copy(record)
        prepared.message = record.getMessage()
        prepared.msg = prepared.message
        prepared.args = None
        if record.exc_info and record.exc_info[0] is not None:
            prepared.diagnostic_error = "".join(traceback.format_exception(*record.exc_info))
        prepared.exc_info = None
        prepared.exc_text = None
        prepared.diagnostic_request_id = REQUEST_CONTEXT.get()
        return prepared

    def emit(self, record: logging.LogRecord) -> None:
        try:
            prepared = self.prepare(record)
            if self.dropped:
                prepared.diagnostic_dropped = self.dropped
            self.queue.put_nowait(prepared)
            self.dropped = 0
        except queue.Full:
            self.dropped += 1
        except Exception:
            self.handleError(record)


def configure_diagnostics(settings: Settings) -> Callable[[], None]:
    """Turn the diagnostic log on when flagged; return the function that stops it.

    With the flag off nothing is created on disk and the diagnostic logger stays disabled.
    """
    if not settings.diagnostic_log:
        return lambda: None

    level = logging.getLevelNamesMapping()[settings.diagnostic_log_level]
    apply_retention(settings.diagnostic_log_dir, DailyFileHandler.day_of(time.time()))
    writer = DailyFileHandler(settings.diagnostic_log_dir)
    writer.setFormatter(JsonLineFormatter(secrets=(settings.telegram_bot_token,)))
    pending: queue.Queue[logging.LogRecord] = queue.Queue(DIAGNOSTIC_QUEUE_RECORDS)
    feeder = DroppingQueueHandler(pending)
    feeder.setLevel(level)
    listener = logging.handlers.QueueListener(pending, writer)

    root = logging.getLogger()
    previous_root_level = root.level
    # The console handler carries its own level, so lowering the root changes only the file.
    root.setLevel(min(root.level, level) if root.level else level)
    root.addHandler(feeder)
    _logger.addHandler(feeder)
    _logger.setLevel(level)
    for name in QUIET_LIBRARIES:
        logging.getLogger(name).setLevel(logging.WARNING)
    listener.start()

    def stop() -> None:
        _logger.setLevel(_DISABLED)
        _logger.removeHandler(feeder)
        root.removeHandler(feeder)
        root.setLevel(previous_root_level)
        listener.stop()
        writer.close()

    return stop


def event(
    stage: str,
    *,
    request: Any = None,
    origin: str = "request",
    level: int = logging.INFO,
    exc_info: Any = None,
    **fields: Any,
) -> None:
    """Record one diagnostic stage. A no-op unless the flag is on."""
    if not _logger.isEnabledFor(level):
        return
    payload: dict[str, Any] = {"origin": origin, "stage": stage}
    if request is not None:
        payload["request_id"] = request.request_id
        payload["platform"] = request.platform
        payload["elapsed_seconds"] = round(time.monotonic() - request.created_at, 4)
    payload.update(fields)
    _logger.log(level, stage, extra={"diagnostic": payload}, exc_info=exc_info)
