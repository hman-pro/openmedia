"""Validated runtime configuration with secret-safe diagnostics."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


MAX_HOSTED_FILE_BYTES = 50_000_000
INSPECTION_SECONDS = 60
SELECTION_SECONDS = 900
PROCESSING_SECONDS = 600
CLEANUP_SECONDS = 900

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

        token = values.get("TELEGRAM_BOT_TOKEN", "")
        if not token or not token.strip():
            raise ConfigError("TELEGRAM_BOT_TOKEN is required")
        if "\x00" in token or "\n" in token or "\r" in token:
            raise ConfigError("TELEGRAM_BOT_TOKEN has an invalid shape")

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

        return cls(
            telegram_bot_token=token,
            work_dir=work_dir,
            max_file_bytes=max_file_bytes,
            max_workers=max_workers,
            max_pending=max_pending,
            workspace_bytes=workspace_bytes,
            log_level=log_level,
        )

    @property
    def redacted_token(self) -> str:
        return "<redacted>"

