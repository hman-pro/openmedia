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

    # Feature 004 (R8): refused links and the resolved short-link address keep their URLs.
    REFUSED_LINKS = ["https://bit.ly/x", "https://lnkd.in/p/dMhfr6kG"]
    RESOLVED_URL = "https://www.linkedin.com/posts/x-share-7508424761698410497-2cX9"

    def test_links_and_resolved_url_are_kept_unredacted(self) -> None:
        entry = render(make_record(origin="input", stage="refused", reason="too_many_links",
            links=self.REFUSED_LINKS, resolution="resolved", resolved_url=self.RESOLVED_URL))
        assert entry["links"] == self.REFUSED_LINKS
        assert entry["resolved_url"] == self.RESOLVED_URL

    def test_urls_in_reason_msg_and_error_are_still_redacted(self) -> None:
        link = self.REFUSED_LINKS[1]
        entry = render(make_record(origin="input", stage="refused", reason=f"bad {link}",
            msg=f"refused {link}", error=f"failed {link}", links=self.REFUSED_LINKS,
            resolved_url=self.RESOLVED_URL))
        for key in ("reason", "msg", "error"):
            assert link not in entry[key]
            assert "<redacted-url>" in entry[key]

    def test_a_token_inside_links_is_still_redacted(self) -> None:
        other = "987654321:BBother-token-shaped-value"
        record = make_record(origin="input", stage="refused", reason="unsupported_link",
            links=[f"https://example.com/bot{TOKEN}/x", f"https://example.com/{other}"])
        line = JsonLineFormatter(secrets=(TOKEN,)).format(record)
        entry = json.loads(line)
        assert TOKEN not in line
        assert "AAEXAMPLE" not in line
        assert other not in line
        assert entry["links"][0].startswith("https://example.com/")
        assert "<redacted-token>" in entry["links"][1]


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


DAY = "2026-09-21"


def lifecycle(created: float, **fields: Any) -> logging.LogRecord:
    return make_record(created=created, origin="lifecycle", stage="sweep", **fields)


def day_file(directory: Path, day: str, size: int = 0) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"openmedia-{day}.log"
    path.write_bytes(b"x" * max(0, size - 1) + (b"\n" if size else b""))
    return path


class TestDayBoundaryAndAppend:
    def handler(self, directory: Path, **kwargs: Any) -> DailyFileHandler:
        handler = DailyFileHandler(directory, **kwargs)
        handler.setFormatter(JsonLineFormatter(secrets=(TOKEN,)))
        return handler

    def test_each_entry_lands_in_the_file_for_its_own_utc_date(self, tmp_path: Path) -> None:
        handler = self.handler(tmp_path)
        handler.emit(lifecycle(at("2026-09-21T23:59:59.900")))
        before = (tmp_path / "openmedia-2026-09-21.log").read_bytes()
        handler.emit(lifecycle(at("2026-09-22T00:00:00.100")))
        handler.emit(lifecycle(at("2026-09-22T00:00:01")))
        handler.close()
        assert (tmp_path / "openmedia-2026-09-21.log").read_bytes() == before
        for path in tmp_path.glob("openmedia-*.log"):
            for line in path.read_text().splitlines():
                assert json.loads(line)["ts"][:10] == path.name[len("openmedia-"):-len(".log")]
        assert len((tmp_path / "openmedia-2026-09-22.log").read_text().splitlines()) == 2

    def test_a_restart_appends_to_the_same_day(self, tmp_path: Path) -> None:
        first = self.handler(tmp_path)
        first.emit(lifecycle(at("2026-09-21T10:00:00"), run=1))
        first.close()
        second = self.handler(tmp_path)
        second.emit(lifecycle(at("2026-09-21T11:00:00"), run=2))
        second.close()
        assert [entry["run"] for entry in read_entries(tmp_path)] == [1, 2]

    def test_a_torn_last_line_is_closed_before_the_next_entry(self, tmp_path: Path) -> None:
        path = tmp_path / f"openmedia-{DAY}.log"
        path.write_text('{"ts":"2026-09-21T09:00:00.000Z","lev')
        handler = self.handler(tmp_path)
        handler.emit(lifecycle(at("2026-09-21T10:00:00")))
        handler.close()
        lines = path.read_text().splitlines()
        assert lines[0] == '{"ts":"2026-09-21T09:00:00.000Z","lev'
        assert json.loads(lines[1])["stage"] == "sweep"


class TestRetention:
    def test_old_day_files_are_removed_by_name_not_mtime(self, tmp_path: Path) -> None:
        import os

        old = day_file(tmp_path, "2026-09-07", 10)   # 14 days before: out
        kept = day_file(tmp_path, "2026-09-08", 10)  # 13 days before: the 14th file
        os.utime(old, None)  # a fresh mtime must not save it
        os.utime(kept, (0, 0))  # an ancient mtime must not condemn it
        diagnostics.apply_retention(tmp_path, DAY)
        assert not old.exists()
        assert kept.exists()

    def test_total_size_is_bounded_oldest_first_and_today_survives(self, tmp_path: Path) -> None:
        for day in ("2026-09-18", "2026-09-19", "2026-09-20", DAY):
            day_file(tmp_path, day, 400)
        remaining = diagnostics.apply_retention(tmp_path, DAY, max_bytes=1000)
        assert sorted(path.name for path in tmp_path.iterdir()) == [
            "openmedia-2026-09-20.log", f"openmedia-{DAY}.log"]
        assert remaining == 400

    def test_unrelated_files_are_never_touched(self, tmp_path: Path) -> None:
        tmp_path.joinpath("notes.log").write_text("mine")
        tmp_path.joinpath("openmedia-2020-01-01.log.bak").write_text("mine")
        tmp_path.joinpath("openmedia-2020-13-45.log").write_text("not a date")
        diagnostics.apply_retention(tmp_path, DAY, max_bytes=1)
        assert len(list(tmp_path.iterdir())) == 3

    def test_a_missing_directory_is_not_created(self, tmp_path: Path) -> None:
        assert diagnostics.apply_retention(tmp_path / "absent", DAY) == 0
        assert not (tmp_path / "absent").exists()

    def test_writing_three_times_the_limit_stays_under_it(self, tmp_path: Path) -> None:
        limit = 20_000
        handler = DailyFileHandler(tmp_path, max_bytes=limit)
        handler.setFormatter(JsonLineFormatter(secrets=()))
        start = at("2026-09-10T12:00:00")
        written = 0
        for day in range(6):
            for index in range(12):
                handler.emit(lifecycle(start + day * 86400 + index, msg="x" * 900))
                written += 900
                assert sum(path.stat().st_size for path in tmp_path.iterdir()) <= limit
        handler.close()
        assert written >= 3 * limit
        assert sorted(path.name for path in tmp_path.iterdir())[-1] == "openmedia-2026-09-15.log"

    def test_a_full_day_pauses_until_tomorrow_with_one_notice(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        handler = DailyFileHandler(tmp_path, max_bytes=2_000)
        handler.setFormatter(JsonLineFormatter(secrets=()))
        for index in range(10):
            handler.emit(lifecycle(at("2026-09-21T10:00:00") + index, msg="x" * 400))
        path = tmp_path / f"openmedia-{DAY}.log"
        assert path.exists() and path.stat().st_size <= 2_000
        assert capsys.readouterr().err.count("size limit") == 1
        handler.emit(lifecycle(at("2026-09-22T00:00:01"), msg="new day"))
        handler.close()
        assert (tmp_path / "openmedia-2026-09-22.log").exists()
        assert not path.exists()  # yesterday made room for today


class TestFailureIsolation:
    def test_unwritable_directory_never_raises_and_notices_once(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = [1000.0]
        directory = tmp_path / "logs"
        handler = DailyFileHandler(directory, clock=lambda: now[0])
        handler.setFormatter(JsonLineFormatter(secrets=()))
        handler.emit(lifecycle(at("2026-09-21T10:00:00")))
        # Root can bypass directory permissions in the CI container. Inject the
        # actual filesystem error so the outage/retry contract is tested there too.
        original_open = diagnostics.os.open

        def denied_open(path: Any, flags: int, mode: int = 0o777) -> int:
            if Path(path).parent == directory:
                raise PermissionError("controlled unwritable diagnostic directory")
            return original_open(path, flags, mode)

        monkeypatch.setattr(diagnostics.os, "open", denied_open)
        try:
            for index in range(5):
                handler.emit(lifecycle(at("2026-09-22T10:00:00") + index))
            assert capsys.readouterr().err.count("diagnostic log unavailable") == 1

            # No retry before the reopen interval, even once the directory is healthy again.
            monkeypatch.setattr(diagnostics.os, "open", original_open)
            now[0] += 59
            handler.emit(lifecycle(at("2026-09-22T10:01:00")))
            assert not (directory / "openmedia-2026-09-22.log").exists()

            now[0] += 2
            handler.emit(lifecycle(at("2026-09-22T10:02:00"), msg="back"))
        finally:
            handler.close()
        entries = [json.loads(line) for line in (directory / "openmedia-2026-09-22.log").read_text().splitlines()]
        assert [entry["stage"] for entry in entries] == ["log_recovered", "sweep"]
        assert entries[0]["lost"] == 6
        assert capsys.readouterr().err.count("diagnostic log recovered") == 1

    def test_a_full_queue_drops_without_blocking_and_reports_the_count(self) -> None:
        import queue
        import time as clock

        pending: queue.Queue[logging.LogRecord] = queue.Queue(2)
        feeder = diagnostics.DroppingQueueHandler(pending)
        started = clock.monotonic()
        for _ in range(5):  # nobody is draining: the writer is stalled
            feeder.emit(lifecycle(at("2026-09-21T10:00:00")))
        assert clock.monotonic() - started < 0.5
        assert feeder.dropped == 3
        pending.get_nowait()
        feeder.emit(lifecycle(at("2026-09-21T10:00:01")))
        pending.get_nowait()
        assert pending.get_nowait().diagnostic_dropped == 3
        assert feeder.dropped == 0

    def test_an_oversized_entry_is_cut_in_order_and_stays_valid(self) -> None:
        formatter = JsonLineFormatter(secrets=(), max_bytes=2_000)
        record = make_record(origin="request", stage="download_finished", request_id=REQUEST_ID,
            msg="m" * 300, error="e" * 5_000, worker_output="w" * 300)
        line = formatter.format(record)
        assert len(line.encode()) + 1 <= 2_000
        entry = json.loads(line)
        assert entry["truncated"] is True
        assert entry["request_id"] == REQUEST_ID
        assert len(entry["error"]) < 5_000 and entry["error"].endswith("[truncated]")
        assert entry["worker_output"] == "w" * 300  # the error alone made enough room
        assert entry["msg"] == "m" * 300

    def test_a_normal_entry_is_not_marked_truncated(self) -> None:
        assert "truncated" not in render(make_record(origin="lifecycle", stage="startup"))


def test_file_loaded_token_redacted_in_console_and_enabled_diagnostics(tmp_path):
    import io
    from openmedia.config import Settings
    from openmedia.__main__ import SafeLogFormatter
    path = tmp_path / 'sentinel-private-path'
    path.write_text(TOKEN)
    settings = Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': str(path),
        'OPENMEDIA_DIAGNOSTIC_LOG': '1', 'OPENMEDIA_DIAGNOSTIC_LOG_DIR': str(tmp_path / 'logs')})
    output = io.StringIO()
    console = logging.StreamHandler(output)
    console.setFormatter(SafeLogFormatter('%(message)s', secrets=(settings.telegram_bot_token,)))
    record = make_record(f'credential {TOKEN}')
    console.handle(record)
    stop = diagnostics.configure_diagnostics(settings)
    try:
        diagnostics.event('sentinel', origin='lifecycle', msg=f'credential {TOKEN}')
    finally:
        stop()
    rendered = output.getvalue() + repr(settings) + ''.join(p.read_text() for p in (tmp_path / 'logs').glob('*'))
    assert TOKEN not in rendered and str(path) not in rendered
