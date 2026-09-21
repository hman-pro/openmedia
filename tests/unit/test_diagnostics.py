from __future__ import annotations

import json
import logging
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from openmedia import diagnostics
from openmedia.diagnostics import DailyFileHandler, JsonLineFormatter


TOKEN = "123456789:AAEXAMPLE-controlled-tests-only-not-a-real-token"
REQUEST_ID = "a" * 32
LINK = "https://www.youtube.com/watch?v=abc123"


def at(text: str) -> float:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()


def make_record(
    message: str = "event",
    *,
    created: float | None = None,
    level: int = logging.INFO,
    name: str = diagnostics.LOGGER_NAME,
    exc_info: Any = None,
    **fields: Any,
) -> logging.LogRecord:
    record = logging.LogRecord(name, level, __file__, 1, message, None, exc_info)
    if fields:
        record.diagnostic = fields
    if created is not None:
        record.created = created
    return record


def render(record: logging.LogRecord) -> dict[str, Any]:
    line = JsonLineFormatter(secrets=(TOKEN,)).format(record)
    assert "\n" not in line
    return json.loads(line)


class TestJsonLineFormatter:
    def test_one_json_object_with_fixed_key_order(self) -> None:
        record = make_record(created=at("2026-09-21T14:03:11.204"), origin="request",
            stage="received", request_id=REQUEST_ID, platform="youtube", elapsed_seconds=0.5)
        entry = render(record)
        assert list(entry)[:5] == ["ts", "level", "origin", "stage", "request_id"]
        assert entry["ts"] == "2026-09-21T14:03:11.204Z"
        assert entry["level"] == "INFO"

    def test_absent_keys_are_omitted_not_null(self) -> None:
        entry = render(make_record(origin="lifecycle", stage="startup", outcome=None))
        assert "request_id" not in entry
        assert "outcome" not in entry
        assert None not in entry.values()

    def test_request_id_falls_back_to_the_context(self) -> None:
        token = diagnostics.REQUEST_CONTEXT.set(REQUEST_ID)
        try:
            entry = render(make_record(origin="request", stage="send_started"))
        finally:
            diagnostics.REQUEST_CONTEXT.reset(token)
        assert entry["request_id"] == REQUEST_ID

    def test_records_without_fields_default_to_library_and_logger_name(self) -> None:
        entry = render(make_record("pool is full", name="somelib.pool"))
        assert entry["origin"] == "library"
        assert entry["stage"] == "somelib.pool"
        assert entry["msg"] == "pool is full"

    def test_existing_console_events_are_lifted_into_fields(self) -> None:
        message = json.dumps({"request_id": REQUEST_ID, "platform": "youtube", "stage": "preview",
            "elapsed_seconds": 1.25})
        entry = render(make_record(message, name="openmedia"))
        assert entry["origin"] == "request"
        assert entry["stage"] == "preview"
        assert entry["request_id"] == REQUEST_ID
        assert "msg" not in entry

    def test_free_text_urls_are_redacted_but_the_submitted_link_is_kept(self) -> None:
        entry = render(make_record(origin="request", stage="received",
            msg=f"fetch {LINK} failed", source_url=LINK, worker_output=f"ERROR: {LINK}&sig=secret"))
        assert entry["source_url"] == LINK
        assert LINK not in entry["msg"]
        assert "<redacted-url>" in entry["msg"]
        assert "sig=secret" not in entry["worker_output"]

    def test_exception_chain_is_rendered_in_full(self) -> None:
        try:
            try:
                raise OSError("disk went away")
            except OSError as inner:
                raise RuntimeError("download failed") from inner
        except RuntimeError as exc:
            record = make_record(origin="request", stage="download_finished",
                exc_info=(type(exc), exc, exc.__traceback__))
        entry = render(record)
        assert "disk went away" in entry["error"]
        assert "download failed" in entry["error"]
        assert "direct cause" in entry["error"]

    def test_token_never_appears(self) -> None:
        try:
            raise RuntimeError(f"bad request to https://api.telegram.org/bot{TOKEN}/send")
        except RuntimeError as exc:
            record = make_record(origin="request", stage="delivery", msg=f"token {TOKEN}",
                source_url=f"https://example.com/?t={TOKEN}", worker_output=f"stderr {TOKEN}",
                exc_info=(type(exc), exc, exc.__traceback__))
        line = JsonLineFormatter(secrets=(TOKEN,)).format(record)
        assert TOKEN not in line
        assert "AAEXAMPLE" not in line


class TestDailyFileHandler:
    def handler(self, directory: Path) -> DailyFileHandler:
        handler = DailyFileHandler(directory)
        handler.setFormatter(JsonLineFormatter(secrets=(TOKEN,)))
        return handler

    def test_nothing_is_created_until_the_first_record(self, tmp_path: Path) -> None:
        directory = tmp_path / "logs"
        handler = self.handler(directory)
        assert not directory.exists()
        handler.close()
        assert not directory.exists()

    def test_first_record_creates_a_private_dated_file(self, tmp_path: Path) -> None:
        directory = tmp_path / "logs"
        handler = self.handler(directory)
        handler.emit(make_record(created=at("2026-09-21T23:59:59"), origin="lifecycle", stage="startup"))
        path = directory / "openmedia-2026-09-21.log"
        assert [item.name for item in directory.iterdir()] == [path.name]
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        handler.close()

    def test_every_write_is_flushed_and_newline_terminated(self, tmp_path: Path) -> None:
        handler = self.handler(tmp_path)
        for index in range(3):
            handler.emit(make_record(created=at("2026-09-21T10:00:00") + index,
                origin="lifecycle", stage="sweep"))
            content = (tmp_path / "openmedia-2026-09-21.log").read_bytes()
            assert content.endswith(b"\n")
            assert content.count(b"\n") == index + 1
        handler.close()


def test_diagnostic_logger_never_propagates_even_before_configuration() -> None:
    logger = logging.getLogger(diagnostics.LOGGER_NAME)
    assert logger.propagate is False
    assert not logger.isEnabledFor(logging.CRITICAL)


def test_redact_matches_the_console_rules() -> None:
    text = f"see {LINK} with {TOKEN} and 987654321:ZZ-other_token"
    result = diagnostics.redact(text, (TOKEN,))
    assert result == "see <redacted-url> with <redacted> and <redacted-token>"


def settings_for(directory: Path, *, enabled: bool = True, level: str = "DEBUG") -> Any:
    from openmedia.config import Settings

    return Settings(telegram_bot_token=TOKEN, diagnostic_log=enabled,
        diagnostic_log_dir=directory, diagnostic_log_level=level)


def read_entries(directory: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for path in sorted(directory.glob("openmedia-*.log"))
        for line in path.read_text(encoding="utf-8").splitlines()]


class TestConfigureDiagnostics:
    def test_flag_off_touches_nothing(self, tmp_path: Path) -> None:
        directory = tmp_path / "logs"
        stop = diagnostics.configure_diagnostics(settings_for(directory, enabled=False))
        diagnostics.event("received", origin="lifecycle", source_url=LINK)
        stop()
        assert not directory.exists()
        assert not logging.getLogger(diagnostics.LOGGER_NAME).isEnabledFor(logging.CRITICAL)

    def test_flag_on_writes_events_and_existing_console_events(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        root = logging.getLogger()
        root.addHandler(console)
        stop = diagnostics.configure_diagnostics(settings_for(tmp_path))
        context = diagnostics.REQUEST_CONTEXT.set(REQUEST_ID)
        try:
            diagnostics.event("received", source_url=LINK, chat_id=1, user_id=2)
            logging.getLogger("openmedia").info(json.dumps({"request_id": REQUEST_ID, "stage": "preview"}))
        finally:
            diagnostics.REQUEST_CONTEXT.reset(context)
            stop()
            root.removeHandler(console)
        entries = read_entries(tmp_path)
        assert [entry["stage"] for entry in entries] == ["received", "preview"]
        assert entries[0]["source_url"] == LINK
        # The request id was captured on the emitting side, not on the writer thread.
        assert entries[0]["request_id"] == REQUEST_ID
        assert LINK not in capsys.readouterr().err

    def test_stop_restores_the_root_logger(self, tmp_path: Path) -> None:
        root = logging.getLogger()
        before = (root.level, list(root.handlers))
        diagnostics.configure_diagnostics(settings_for(tmp_path))()
        assert (root.level, list(root.handlers)) == before
