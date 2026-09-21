---
description: "Implementation tasks for OpenMedia's flagged diagnostic log file"
---

# Tasks: Diagnostic Log File

**Input**: Design documents from `specs/002-file-logging/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md).

**Tests**: Included, because SC-002 to SC-009 and quickstart §1 are defined as automated
proofs and the constitution requires validation on controlled fixtures. Write each story's
tests before its behavior and observe the expected failure. All tests are offline, use
`tmp_path`, and never go under `tests/live/`.

**Organization**: Three user stories in priority order: US1 trace a request (P1), US2 daily
files that persist and stay bounded (P2), US3 flag and configuration control (P3). Every
task starts unchecked.

## Format: `[ID] [P?] [Story] Description`

`[P]` means a different file with no dependency on an unfinished task. Story phases carry
`[US1]`, `[US2]`, or `[US3]`. Paths are relative to the repository root. §N refers to
[research.md](research.md).

## Path Conventions

Application: `src/openmedia/`; tests: `tests/`; feature documents: `specs/002-file-logging/`.
Standard library only: no change to `pyproject.toml` dependencies or `uv.lock`. No database,
queue service, or second process writes log files.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Make sure a log file can never be committed or baked into the image, and that
the container has a place to write.

- [X] T001 [P] Add `logs/` and `*.log` under a "Diagnostic logs — may contain links and Telegram identifiers" comment in `.gitignore`, and the same two patterns in `.dockerignore` (FR-016).
- [X] T002 [P] In `Dockerfile`, in the same `RUN` that creates UID/GID 10001, add `mkdir -p /var/log/openmedia && chown 10001:10001 /var/log/openmedia && chmod 0700 /var/log/openmedia` so a named volume mounted there inherits ownership (§10).
- [X] T003 [P] Add to `.env.example`, commented out with one-line explanations: `OPENMEDIA_DIAGNOSTIC_LOG=0`, `OPENMEDIA_DIAGNOSTIC_LOG_DIR=/var/log/openmedia`, `OPENMEDIA_DIAGNOSTIC_LOG_LEVEL=DEBUG`. State that the flag is for development and that the file holds submitted links and Telegram identifiers.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Settings, the redaction move, and the write pipeline. Nothing in a story phase
can be built before this. Flag-off behavior must be unchanged at the end of this phase.

- [X] T004 [P] Write failing tests in `tests/unit/test_config_diagnostics.py` for `Settings.from_env`: flag absent → `diagnostic_log is False`; `OPENMEDIA_DIAGNOSTIC_LOG` accepts "Exactly `0` or `1`; anything else is a `ConfigError`" (test `true`, `yes`, empty string, ` 1`); defaults `diagnostic_log_dir == Path("/var/log/openmedia")` and `diagnostic_log_level == "DEBUG"`. Directory and level validation cases belong to T027.
- [X] T005 Add to `src/openmedia/config.py`: constants `DIAGNOSTIC_LOG_MAX_DAYS = 14`, `DIAGNOSTIC_LOG_MAX_BYTES = 50_000_000`, `DIAGNOSTIC_ENTRY_MAX_BYTES = 65_536`, `DIAGNOSTIC_QUEUE_RECORDS = 10_000`, `DIAGNOSTIC_REOPEN_SECONDS = 60`; `Settings` fields `diagnostic_log: bool = False`, `diagnostic_log_dir: Path = Path("/var/log/openmedia")`, `diagnostic_log_level: str = "DEBUG"`; flag parsing in `from_env` per T004. Make T004 pass. Do not validate directory or level yet.
- [X] T006 Create `src/openmedia/diagnostics.py` with a module-level `redact(text: str, secrets: tuple[str, ...]) -> str` holding the exact three-step logic now in `SafeLogFormatter.format` (secrets → `<redacted>`, `https?://[^\s"'<>]+` → `<redacted-url>`, `\b\d{6,}:[A-Za-z0-9_-]+` → `<redacted-token>`). Change `SafeLogFormatter.format` in `src/openmedia/__main__.py` to call it. `diagnostics.py` must not import from `__main__`. Run `uv run pytest`; console behavior must be unchanged.
- [X] T007 [P] Write failing tests in `tests/unit/test_diagnostics.py` for `JsonLineFormatter`: output is one line of valid JSON ending without embedded newlines; key order is `ts, level, origin, stage, request_id, msg, …` per data-model; `ts` is "RFC 3339 UTC, millisecond precision, `Z` suffix"; absent keys are "omitted, not null"; `request_id` is filled from `REQUEST_CONTEXT` when the record has none; `msg`, `error`, and `worker_output` are URL- and token-redacted; `source_url` is token-redacted only and keeps its URL; an exception with `__cause__` renders the whole chain in `error`; the bot token forced into `msg`, the exception text, and `worker_output` appears zero times (SC-005).
- [X] T008 Implement `JsonLineFormatter(secrets)` in `src/openmedia/diagnostics.py` to pass T007. Read structured fields from a `record.diagnostic` dict set via `extra`; default `origin` to `library` and `stage` to the logger name for records that carry no dict. Move `REQUEST_CONTEXT` into `diagnostics.py` and re-export it from `src/openmedia/__main__.py` so existing imports keep working.
- [X] T009 [P] Write failing tests in `tests/unit/test_diagnostics.py` for `DailyFileHandler(directory, clock=...)`: first record creates the directory with mode `0700` and `openmedia-YYYY-MM-DD.log` with mode `0600`, named from the record's UTC date; every write ends in `\n` and is flushed; nothing is created on construction, only on first record.
- [X] T010 Implement `DailyFileHandler` in `src/openmedia/diagnostics.py` to pass T009: choose the file from each record's `created` timestamp in UTC, open in append mode, keep one open file, hold the states `closed` and `open(day)` from data-model. Day rollover, retention, pause, and degraded mode are added in Phase 4.
- [X] T011 Add `configure_diagnostics(settings) -> Callable[[], None]` and `event(stage, *, request=None, origin="request", level=logging.INFO, exc_info=None, **fields)` in `src/openmedia/diagnostics.py`. Flag off: attach a `NullHandler` to logger `openmedia.diagnostic`, set `propagate = False`, return a no-op stopper, touch no filesystem. Flag on: build `DailyFileHandler` + `JsonLineFormatter`, wrap in `QueueListener` fed by a `QueueHandler` over `queue.Queue(DIAGNOSTIC_QUEUE_RECORDS)`; attach the `QueueHandler` to `openmedia.diagnostic` (`propagate = False`) and to the root logger beside the console handler; on `queue.Full` drop the record and count it, writing `dropped` on the next entry; return a stopper that calls `listener.stop()`. `event()` fills `request_id`, `platform`, and `elapsed_seconds` from `request` when given. Keep `httpx`, `httpcore`, `telegram`, `urllib3`, `requests` capped at `WARNING` (§11).
- [X] T012 Wire `src/openmedia/__main__.py`: call `configure_diagnostics(settings)` in `main()` only on the polling path, after the `--check-config` return and never for `--healthcheck` (§12); set the console handler's own level to `settings.log_level` and the root level to the lower of the console and file levels so the console output is unchanged; call the stopper in a `finally` around `run_polling`. Run `uv run pytest`; all existing tests pass.

**Checkpoint**: With `OPENMEDIA_DIAGNOSTIC_LOG=1` the existing `openmedia` events appear in
a day file. With the flag off nothing is created and the full suite is green.

---

## Phase 3: User Story 1 - Trace one failed request end to end (Priority: P1) 🎯 MVP

**Goal**: Every stage of a request is in the file under one `request_id`, and a failure
names its stage, cause, deadline, error chain, and worker output.

**Independent Test**: Run a stubbed failing download with the flag on, then
`grep <request_id>` the day file: the entries run from `received` to `terminal`, and the
failing entry carries `failed_stage`, `error_category`, and `error` or `worker_output`.

### Tests for User Story 1

- [ ] T013 [US1] Write failing tests in `tests/integration/test_diagnostic_trace.py` using the existing fake Telegram transport and `tests/fixtures/worker_stub.py`, flag on, log dir in `tmp_path`, listener stopped before asserting. Four flows: success, worker failure during download, selection expiry, inspection timeout. Assert per flow that every expected stage from the data-model stage table is present under one `request_id` (SC-002): success = `received, acknowledgment, inspection_started, inspection_finished, preview, selection, download_started, download_finished, send_started, delivery, cleanup, terminal`. Assert the failure flow's entry has `level == "ERROR"`, `failed_stage`, `error_category`, and non-empty `worker_output`; the timeout flow has `deadline == "inspection"` and `deadline_seconds == 60`; the expiry flow has stage `expired` with `deadline == "selection"` and `deadline_seconds == 900`.
- [ ] T014 [US1] In the same file, assert identifier placement (FR-009, §6): exactly one entry per request has `source_url`, `chat_id`, and `user_id`, and it is the `received` entry; no entry has a name, username, or message text field; captured stderr for the whole run contains neither the submitted link nor the string `source_url`.

### Implementation for User Story 1

- [ ] T015 [US1] In `src/openmedia/coordinator.py`, emit `event("received", request=request, source_url=request.source_url, chat_id=request.chat_id, user_id=request.user_id)` where `MediaWorkflow.submit` creates the request; `event("selection", request=request, option_id=...)` where `select` claims the selection; `event("expired", request=request, deadline="selection", deadline_seconds=900, level=logging.WARNING)` for each request expired by `expire_pending`. `option_id` is an integer, never a URL or path.
- [ ] T016 [US1] In `src/openmedia/__main__.py`, emit `inspection_started` and `inspection_finished` (with `outcome`) around the inspection worker call, `download_started`/`download_finished` (with `outcome`, `bytes`) around the download worker call, and `send_started` before the Telegram upload. Leave the existing `observe()` stages (`acknowledgment`, `preview`, `delivery`, `source_response`, `telegram_response`, `terminal`) and their console JSON untouched.
- [ ] T017 [US1] In `src/openmedia/__main__.py`, on every failure path that reaches `notify_failure` or catches a worker/delivery exception, emit the failing stage's `_finished` event at `logging.ERROR` with `error_category`, `failed_stage`, `exc_info` for the full chain (FR-004), and for deadline failures `deadline` ∈ {`inspection`, `processing`, `cleanup`} with `deadline_seconds` ∈ {60, 600, 900} taken from the `config.py` constants (FR-005).
- [ ] T018 [US1] In `src/openmedia/workers.py`, where a supervised worker ends in failure, pass the already-sanitized `last_stderr` (decoded with `errors="replace"`) to the caller so T017's event includes it as `worker_output` (FR-006, §7). Do not change `_read_stderr`'s redaction or byte limit, and do not log from the worker subprocess.
- [ ] T019 [US1] Emit `event("cleanup", request=request, outcome="removed"|"deferred")` in `src/openmedia/__main__.py` where the request workspace is cleaned up, beside the existing "workspace cleanup deferred" warning. Make T013 and T014 pass, then run `uv run pytest`.

**Checkpoint**: US1 is usable as the MVP: one file for the current day, complete traces.

---

## Phase 4: User Story 2 - One file per day that survives restarts and stays bounded (Priority: P2)

**Goal**: A new file each UTC day, append after restart, whole-file retention within 14 day
files and 50,000,000 bytes, lifecycle entries, and no request harmed by a log failure.

**Independent Test**: With an injected clock, write across 00:00 UTC and see two correctly
named files; reopen the handler and see appended lines; write three times the size limit and
see the directory at or under the limit with today's file intact.

### Tests for User Story 2

- [ ] T020 [P] [US2] Write failing tests in `tests/unit/test_diagnostics.py`: clock crossing 00:00 UTC puts each entry in the file named for its `ts` date and leaves the earlier file byte-identical (SC-009); a second handler on the same day appends and earlier lines are intact (SC-003); a file that "does not end in a newline" gets one before the next entry.
- [ ] T021 [P] [US2] Write failing tests in `tests/unit/test_diagnostics.py` for retention: files whose name date is more than 14 days before today are removed, judged by name and not mtime; after writing three times `DIAGNOSTIC_LOG_MAX_BYTES` across several days the directory total is at or under 50,000,000 bytes with the newest kept (SC-004); today's file is never removed, and when it alone reaches the limit the handler enters `paused(day)`, writes nothing more that day, prints exactly one stderr line, and resumes on the next day; files not matching `openmedia-\d{4}-\d{2}-\d{2}\.log` (for example `notes.log`, `openmedia-2026-09-21.log.bak`) are never touched.
- [ ] T022 [P] [US2] Write failing tests in `tests/unit/test_diagnostics.py` for failure isolation: with the directory made unwritable mid-run `emit` does not raise and stderr gets exactly one notice (SC-006); a reopen is attempted no sooner than `DIAGNOSTIC_REOPEN_SECONDS` later, and on success a `log_recovered` entry is written and stderr gets one recovery line; with the listener's handler blocked, `event()` returns immediately and a full queue produces a `dropped` count on the next written entry (SC-007); an entry over 65,536 bytes is cut in the order `error`, `worker_output`, `msg`, stays valid JSON, and has `truncated: true` (FR-017).

### Implementation for User Story 2

- [ ] T023 [US2] Extend `DailyFileHandler` in `src/openmedia/diagnostics.py` with the remaining data-model states: day rollover (`open(day)` → close → retention → `open(new day)`), the newline guard on open, `paused(day)`, and `degraded` via an overridden `handleError` with the one-notice and 60 s reopen rules. Make T020 and T022's handler cases pass.
- [ ] T024 [US2] Add `apply_retention(directory, today)` in `src/openmedia/diagnostics.py` implementing §8 exactly, call it from `configure_diagnostics` at start and from the handler on rollover, and add entry truncation to `JsonLineFormatter`. Make T021 and the rest of T022 pass.
- [ ] T025 [US2] In `src/openmedia/__main__.py`, emit lifecycle events with `origin="lifecycle"`: `startup` with the effective settings from `Settings` excluding `telegram_bot_token`; `shutdown` with `reason` `signal` or `error` from `stop()`; `crash` with `exc_info` from an exception escaping `run_polling`. Emit `event("sweep", origin="sweep", expired=<n>, cleanup_retried=<n>, cleanup_failed=<n>)` once per `maintain` iteration that did any work. Ensure the stopper runs after `shutdown` is queued and inside the existing 20 s exit budget.
- [ ] T026 [US2] Add to `tests/integration/test_diagnostic_trace.py`: build the application twice against one `tmp_path` log dir and assert one day file containing two `startup` entries with a `shutdown` between them; assert a request in flight while the directory becomes unwritable ends with the same user-visible outcome as the baseline run (SC-006).

**Checkpoint**: The flag can be left on for days without filling the disk.

---

## Phase 5: User Story 3 - Control location and detail without code changes (Priority: P3)

**Goal**: Directory and level are validated when the flag is on, ignored when it is off, and
flag-off leaves nothing behind.

**Independent Test**: `--check-config` exits 2 naming `OPENMEDIA_DIAGNOSTIC_LOG_DIR` for an
unwritable path, exits 0 for a good one, and with the flag off creates no file or directory.

### Tests for User Story 3

- [ ] T027 [P] [US3] Extend `tests/unit/test_config_diagnostics.py`: flag on rejects a directory that is not "absolute, no NUL, not equal to or inside `work_dir`" and a level outside `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`; flag off accepts any value for both without error (FR-013); error text names the variable and contains no token.
- [ ] T028 [P] [US3] Add tests in `tests/unit/test_diagnostics.py` and `tests/integration/test_diagnostic_trace.py`: flag off leaves zero files and zero directories under the configured path after a full request flow and after `main(["--check-config"])` (SC-008); flag on, `--check-config` with an unwritable directory returns 2 with a message naming the path and reason, and with a writable one returns 0, leaves the directory empty (probe removed), and writes no entries; `--healthcheck` never creates the directory; `OPENMEDIA_DIAGNOSTIC_LOG_LEVEL=INFO` drops `DEBUG` entries from the file while `DEBUG` keeps them.

### Implementation for User Story 3

- [ ] T029 [US3] Add the flag-on directory and level validation to `Settings.from_env` in `src/openmedia/config.py` per T027, reusing the `_LOG_LEVELS` set.
- [ ] T030 [US3] In `validate_local_runtime` in `src/openmedia/__main__.py`, when `settings.diagnostic_log` is true: create the directory with mode `0700`, reject a symlink or non-directory, write and unlink `.diagnostic-probe`, and raise `ConfigError(f"OPENMEDIA_DIAGNOSTIC_LOG_DIR {path} is not writable: {reason}")` on `OSError`. Skip entirely when the flag is off. Add `diagnostic_log=on|off` (and the directory when on) to the `--check-config` success line.
- [ ] T031 [US3] Apply `settings.diagnostic_log_level` to the file handler in `configure_diagnostics` in `src/openmedia/diagnostics.py`, emit worker protocol messages and coalesced progress as `logging.DEBUG` events from `src/openmedia/__main__.py`, and make T027 and T028 pass.

**Checkpoint**: All three stories work independently; `uv run pytest` is green.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T032 [P] Apply the four amendments listed in `specs/002-file-logging/contracts/diagnostic-log.md` to `specs/001-media-download/contracts/runtime.md` and `specs/001-media-download/contracts/source-adapters.md`, each marked "(amended by 002)".
- [ ] T033 [P] Document the flag in `README.md`: the three variables, the `-v openmedia-logs:/var/log/openmedia` mount added to the existing `docker run` example, the local `OPENMEDIA_DIAGNOSTIC_LOG_DIR=$PWD/logs` recipe, the `grep`/`jq` trace commands from quickstart §2, and a plain statement that the files contain submitted links and Telegram identifiers for up to 14 days.
- [ ] T034 [P] Update `CLAUDE.md`: add `specs/002-file-logging/` rows to "Where truth lives", and add one constraint bullet: links and Telegram identifiers are logged only through `openmedia.diagnostic`, never through a logger that reaches the console.
- [ ] T035 Run quickstart §1 to §4 and record commands, results, and date in `specs/002-file-logging/validation.md`. Run the container check in quickstart §5 if Docker and a test token are available; otherwise record it as "not run", never as passed.

---

## Dependencies & Execution Order

- **Phase 1** has no dependencies; T001 to T003 run in parallel.
- **Phase 2** blocks every story. Order: T004 → T005; T006 → T007 → T008; T009 → T010;
  then T011 → T012. T004, T007, and T009 can be written in parallel.
- **US1 (Phase 3)** needs Phase 2 only. T013 → T014 (same file); T015, T016 → T017 → T018
  → T019. T015 (`coordinator.py`) can run beside T016 (`__main__.py`).
- **US2 (Phase 4)** needs Phase 2 only; it does not need US1. T026 reuses US1's test file,
  so write it after T013 if both stories are in progress.
- **US3 (Phase 5)** needs Phase 2 only. T028's level case needs at least one `DEBUG` event,
  which T031 adds.
- **Phase 6** needs all stories. T032 to T034 are parallel; T035 is last.
- Project rhythm: one commit per phase, `feat(002): phase N <name>`, and mark each task
  `[X]` as it finishes.

## Parallel Example: Phase 2 test-first batch

```text
T004 tests/unit/test_config_diagnostics.py   (settings and flag parsing)
T007 tests/unit/test_diagnostics.py          (formatter)  ─┐ same file: write T007 then T009,
T009 tests/unit/test_diagnostics.py          (handler)    ─┘ or split into two sessions by class
```

## Parallel Example: User Story 2 tests

```text
T020 day boundary and append      T021 retention      T022 failure isolation and truncation
```

All three are in `tests/unit/test_diagnostics.py` as separate test classes; they are
independent in content, so they parallelize only if each author owns one class.

## Implementation Strategy

1. **MVP**: Phases 1 to 3. That gives a complete trace in a dated file with the flag on.
   Without Phase 4 the file has no retention, so keep the flag on only while investigating.
2. **Make it safe to leave on**: Phase 4.
3. **Make it safe to misconfigure**: Phase 5.
4. **Close the documents**: Phase 6.

Stop after each phase, run `uv run pytest`, commit, then continue.
