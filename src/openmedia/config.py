"""Validated runtime configuration with secret-safe diagnostics."""

from __future__ import annotations

import logging
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


MAX_HOSTED_FILE_BYTES = 50_000_000
INSPECTION_SECONDS = 60
SELECTION_SECONDS = 900
PROCESSING_SECONDS = 600
CLEANUP_SECONDS = 900
# Diagnostic log limits are fixed like the deadlines (specs/002-file-logging, FR-010/FR-017).
DIAGNOSTIC_LOG_MAX_DAYS = 14
DIAGNOSTIC_LOG_MAX_BYTES = 50_000_000
DIAGNOSTIC_ENTRY_MAX_BYTES = 65_536
DIAGNOSTIC_QUEUE_RECORDS = 10_000
DIAGNOSTIC_REOPEN_SECONDS = 60

_FIXED_PREFIXES = (
    "OPENMEDIA_INSPECTION",
    "OPENMEDIA_SELECTION",
    "OPENMEDIA_PROCESSING",
    "OPENMEDIA_CLEANUP",
)
_LOG_LEVELS = frozenset(
    name for name in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")
)


class ConfigError(ValueError):
    """A configuration error whose text is safe to show without redaction."""


def _file_token(raw_path: str) -> str:
    """Load one bounded regular-file secret without printable filesystem errors."""
    if not raw_path or "\x00" in raw_path or not Path(raw_path).is_absolute():
        raise ConfigError("TELEGRAM_BOT_TOKEN_FILE: invalid path") from None
    try:
        descriptor = os.open(raw_path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ConfigError("TELEGRAM_BOT_TOKEN_FILE: nonregular file") from None
            chunks: list[bytes] = []
            remaining = 4097
            while remaining:
                chunk = os.read(descriptor, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
        finally:
            os.close(descriptor)
    except UnicodeEncodeError:
        raise ConfigError("TELEGRAM_BOT_TOKEN_FILE: invalid path") from None
    except OSError:
        raise ConfigError("TELEGRAM_BOT_TOKEN_FILE: unreadable file") from None
    if len(content) > 4096:
        raise ConfigError("TELEGRAM_BOT_TOKEN_FILE: oversized file") from None
    try:
        token = content.decode("ascii")
    except UnicodeDecodeError:
        raise ConfigError("TELEGRAM_BOT_TOKEN_FILE: invalid encoding") from None
    if token.endswith("\r\n"):
        token = token[:-2]
    elif token.endswith("\n"):
        token = token[:-1]
    if not token:
        raise ConfigError("TELEGRAM_BOT_TOKEN_FILE: empty content") from None
    if re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token) is None:
        raise ConfigError("TELEGRAM_BOT_TOKEN_FILE: invalid token shape") from None
    return token


def _positive_integer(values: Mapping[str, str], name: str, default: int) -> int:
    raw = values.get(name, str(default))
    try:
        value = int(raw, 10)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """The complete supported environment surface.

    Deadline values are constants rather than fields loaded from the environment. The bot
    token is intentionally excluded from dataclass representations.
    """

    telegram_bot_token: str = field(repr=False)
    work_dir: Path = Path("/tmp/openmedia")
    max_file_bytes: int = MAX_HOSTED_FILE_BYTES
    max_workers: int = 2
    max_pending: int = 100
    workspace_bytes: int = 128 * 1024 * 1024
    log_level: str = "INFO"
    diagnostic_log: bool = False
    diagnostic_log_dir: Path = Path("/var/log/openmedia")
    diagnostic_log_level: str = "DEBUG"
    inspection_seconds: int = field(default=INSPECTION_SECONDS, init=False)
    selection_seconds: int = field(default=SELECTION_SECONDS, init=False)
    processing_seconds: int = field(default=PROCESSING_SECONDS, init=False)
    cleanup_seconds: int = field(default=CLEANUP_SECONDS, init=False)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if environ is None else environ

        overridden = sorted(
            name
            for name in values
            if any(name.startswith(prefix) for prefix in _FIXED_PREFIXES)
        )
        if overridden:
            raise ConfigError(
                "inspection, selection, processing, and cleanup deadlines are fixed by "
                "the specification and cannot be configured"
            )

        if "TELEGRAM_BOT_TOKEN" in values and "TELEGRAM_BOT_TOKEN_FILE" in values:
            raise ConfigError("TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN_FILE are mutually exclusive")
        if "TELEGRAM_BOT_TOKEN_FILE" in values:
            token = _file_token(values["TELEGRAM_BOT_TOKEN_FILE"])
        elif "TELEGRAM_BOT_TOKEN" in values:
            token = values["TELEGRAM_BOT_TOKEN"]
            if not token or not token.strip():
                raise ConfigError("TELEGRAM_BOT_TOKEN is required")
            if "\x00" in token or "\n" in token or "\r" in token:
                raise ConfigError("TELEGRAM_BOT_TOKEN has an invalid shape")
        else:
            raise ConfigError("TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN_FILE is required")

        raw_work_dir = values.get("OPENMEDIA_WORK_DIR", "/tmp/openmedia")
        work_dir = Path(raw_work_dir)
        if not work_dir.is_absolute() or "\x00" in raw_work_dir:
            raise ConfigError("OPENMEDIA_WORK_DIR must be an absolute path")

        max_file_bytes = _positive_integer(
            values, "OPENMEDIA_MAX_FILE_BYTES", MAX_HOSTED_FILE_BYTES
        )
        if max_file_bytes > MAX_HOSTED_FILE_BYTES:
            raise ConfigError(
                f"OPENMEDIA_MAX_FILE_BYTES cannot exceed {MAX_HOSTED_FILE_BYTES}"
            )
        max_workers = _positive_integer(values, "OPENMEDIA_MAX_WORKERS", 2)
        max_pending = _positive_integer(values, "OPENMEDIA_MAX_PENDING", 100)
        workspace_bytes = _positive_integer(
            values, "OPENMEDIA_WORKSPACE_BYTES", 128 * 1024 * 1024
        )
        if workspace_bytes < 2 * max_file_bytes:
            raise ConfigError(
                "OPENMEDIA_WORKSPACE_BYTES must be at least twice "
                "OPENMEDIA_MAX_FILE_BYTES"
            )

        log_level = values.get("OPENMEDIA_LOG_LEVEL", "INFO").upper()
        if log_level not in _LOG_LEVELS or logging.getLevelName(log_level) == "Level INFO":
            raise ConfigError("OPENMEDIA_LOG_LEVEL must be CRITICAL, ERROR, WARNING, INFO, or DEBUG")

        raw_flag = values.get("OPENMEDIA_DIAGNOSTIC_LOG", "0")
        if raw_flag not in {"0", "1"}:
            raise ConfigError("OPENMEDIA_DIAGNOSTIC_LOG must be 0 or 1")
        diagnostic_log = raw_flag == "1"
        # Location and detail are validated only when the flag is on (002 FR-013): a stale
        # value must not stop a bot that is not using the diagnostic log.
        diagnostic_log_dir = Path("/var/log/openmedia")
        diagnostic_log_level = "DEBUG"
        if diagnostic_log:
            raw_log_dir = values.get("OPENMEDIA_DIAGNOSTIC_LOG_DIR", str(diagnostic_log_dir))
            diagnostic_log_dir = Path(os.path.normpath(raw_log_dir)) if raw_log_dir else Path("")
            if not diagnostic_log_dir.is_absolute() or "\x00" in raw_log_dir:
                raise ConfigError("OPENMEDIA_DIAGNOSTIC_LOG_DIR must be an absolute path")
            # The work directory is emptied at every start, which would delete the logs.
            normalized_work_dir = Path(os.path.normpath(work_dir))
            if diagnostic_log_dir == normalized_work_dir or normalized_work_dir in diagnostic_log_dir.parents:
                raise ConfigError("OPENMEDIA_DIAGNOSTIC_LOG_DIR must be outside OPENMEDIA_WORK_DIR")
            diagnostic_log_level = values.get("OPENMEDIA_DIAGNOSTIC_LOG_LEVEL", "DEBUG").upper()
            if diagnostic_log_level not in _LOG_LEVELS:
                raise ConfigError(
                    "OPENMEDIA_DIAGNOSTIC_LOG_LEVEL must be CRITICAL, ERROR, WARNING, INFO, or DEBUG"
                )

        return cls(
            telegram_bot_token=token,
            work_dir=work_dir,
            max_file_bytes=max_file_bytes,
            max_workers=max_workers,
            max_pending=max_pending,
            workspace_bytes=workspace_bytes,
            log_level=log_level,
            diagnostic_log=diagnostic_log,
            diagnostic_log_dir=diagnostic_log_dir,
            diagnostic_log_level=diagnostic_log_level,
        )

    @property
    def redacted_token(self) -> str:
        return "<redacted>"

