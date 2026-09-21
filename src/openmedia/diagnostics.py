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
import time
import traceback
from collections.abc import Callable
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any

from openmedia.config import DIAGNOSTIC_QUEUE_RECORDS, Settings


LOGGER_NAME = "openmedia.diagnostic"
REQUEST_CONTEXT: ContextVar[str | None] = ContextVar("request_id", default=None)
QUIET_LIBRARIES = ("httpx", "httpcore", "telegram", "urllib3", "requests")

_URL = re.compile(r"https?://[^\s\"'<>]+")
_TOKEN = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]+")
_DISABLED = logging.CRITICAL + 1
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

    def __init__(self, *, secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.secrets = secrets

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
            if isinstance(value, str):
                clean = redact_secrets if key in _KEEPS_URL else redact
                value = clean(value, self.secrets)
            entry[key] = value
        return entry

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(self.entry(record), separators=(",", ":"), ensure_ascii=False, default=str)


class DailyFileHandler(logging.Handler):
    """Append each record to ``openmedia-YYYY-MM-DD.log`` for the record's own UTC date."""

    def __init__(self, directory: Path, *, clock: Callable[[], float] = time.time) -> None:
        super().__init__()
        self.directory = Path(directory)
        self.clock = clock
        self._day: str | None = None
        self._stream: IO[str] | None = None

    @staticmethod
    def day_of(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")

    def path_for(self, day: str) -> Path:
        return self.directory / f"openmedia-{day}.log"

    def _open(self, day: str) -> IO[str]:
        self._close_stream()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(self.path_for(day), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        self._stream = os.fdopen(descriptor, "a", encoding="utf-8")
        self._day = day
        return self._stream

    def _close_stream(self) -> None:
        stream, self._stream, self._day = self._stream, None, None
        if stream is not None:
            stream.close()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            day = self.day_of(record.created)
            stream = self._stream if self._stream is not None and day == self._day else self._open(day)
            stream.write(self.format(record) + "\n")
            stream.flush()
        except Exception:
            self.handleError(record)

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
