# Implementation Plan: Diagnostic Log File

**Branch**: `002-file-logging` | **Date**: 2026-09-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-file-logging/spec.md`

**Note**: This template is filled in by the `$speckit-plan` command; its definition describes the execution workflow.

## Summary

Add a development-time diagnostic log behind a feature flag that is off by default. With
`OPENMEDIA_DIAGNOSTIC_LOG=1`, the bot writes one JSON Lines file per UTC day,
`openmedia-YYYY-MM-DD.log`, covering every request stage, deadline expiries, full error
chains, sanitized worker output, and process lifecycle. The submitted link and Telegram
identifiers appear once per request, on the `received` entry, and only in the file.

Technical approach ([research.md](research.md)): standard library `logging` only. A new
module, `src/openmedia/diagnostics.py`, holds a per-record daily file handler, a JSON
formatter that reuses the existing redaction, name-based retention, and an `event()` helper.
Records travel through a bounded `QueueHandler`/`QueueListener` so the asyncio loop never
waits on disk. New stage events use a dedicated non-propagating logger, so console output
stays byte-identical and identifying data cannot reach it.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Standard library only (`logging`, `logging.handlers`, `queue`,
`json`, `traceback`). No change to `pyproject.toml` dependencies or `uv.lock`.

**Storage**: Append-only text files in `OPENMEDIA_DIAGNOSTIC_LOG_DIR` (default
`/var/log/openmedia`), on an operator-mounted volume. Not application state; never read back
by the bot.

**Testing**: pytest with `tmp_path`, an injected clock for day boundaries, and the existing
fake Telegram transport and `worker_stub.py`. No network; nothing under `tests/live/`.

**Target Platform**: The existing single Linux container (UID/GID 10001, read-only image
filesystem), and macOS/Linux for local development.

**Project Type**: Single-process Telegram bot service with a CLI entry point.

**Performance Goals**: Logging cost on the event loop is one non-blocking queue put per
record. End-to-end request time stays within 5% of flag-off (SC-007).

**Constraints**: 14 day files, 50,000,000 bytes total, 65,536 bytes per entry, queue of
10,000 records, all fixed in code. Flag off creates nothing on disk. Console output
unchanged. Token never written. Only the parent process writes files.

**Scale/Scope**: One operator, one bot instance, at most two workers. Roughly 15 to 20
entries per request. One new module of about 250 lines, edits to four existing modules,
three new test files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Evidence |
|---|---|---|
| I. Serves downloading or its operation | Pass | Diagnoses failed downloads; adds no platform or media type |
| II. Telegram is the interface; download logic separate from message handling | Pass | No user-visible change. Logging lives in its own module; `bot.py` gains no file handling |
| III. Python by default; simplest arrangement; no extra service | Pass | Standard library, same process. `queue.Queue` is an in-process object |
| IV. Evaluate open source before custom code; record dependencies | Pass | research §1 and §2 evaluate `loguru`, `structlog`, `TimedRotatingFileHandler`. Custom handler justified by FR-019 and FR-010. No new dependency to record |
| V. Container deployment; storage documented; config at runtime | Pass | Contract documents the optional volume and three env variables. Quickstart §5 verifies the container |
| Timeout, concurrency, temp-storage limits; cleanup policy | Pass | Log storage bounded by fixed limits with documented retention. Temporary media policy untouched |
| Token excluded from logs and version control | Pass | Existing redaction reused in the file formatter; SC-005 test. `logs/` and `*.log` ignored |
| Database, queue, or service only with a documented requirement | Pass | None added |
| Spec → plan → tasks; validation on controlled fixtures | Pass | This plan. All new tests are offline; the one Docker check is labeled separately |

Project constraints in `CLAUDE.md`: state stays in memory (the log is never read back);
deadlines stay fixed (logged, not changed); callback data untouched; token stays out of
logs.

**Initial gate**: Pass, no violations. **Post-design re-check**: Pass. The design added no
dependency, service, or state. One point needed care and is resolved in research §6 and §7:
feature 001 promised that links and worker output never reach routine logs. That holds for
the console; the flagged file is a named exception, written into the 001 contracts as
amendments.

## Project Structure

### Documentation (this feature)

```text
specs/002-file-logging/
├── plan.md              # This file
├── research.md          # Phase 0: 12 decisions
├── data-model.md        # Phase 1: settings, day file, entry fields, stages, handler states
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   └── diagnostic-log.md  # Env variables, guarantees, line format, deployment, 001 amendments
├── checklists/
│   └── requirements.md
└── tasks.md             # Created by /speckit-tasks, not by this command
```

### Source Code (repository root)

```text
src/openmedia/
├── diagnostics.py       # NEW: DailyFileHandler, JsonLineFormatter, retention,
│                        #      configure_diagnostics(), event()
├── config.py            # EDIT: three settings, five constants, validation when flag is on
├── __main__.py          # EDIT: move redaction where diagnostics can import it; wire
│                        #       configure_diagnostics after --check-config returns;
│                        #       startup/shutdown/crash events; new stage events;
│                        #       directory probe in validate_local_runtime
├── coordinator.py       # EDIT: received, selection, expired events
├── workers.py           # EDIT: worker_output on failure; download and cleanup events
└── bot.py               # unchanged

tests/
├── unit/
│   ├── test_diagnostics.py          # NEW: handler, formatter, retention, truncation, degraded mode
│   └── test_config_diagnostics.py   # NEW: flag parsing, directory rules, flag-off ignores dir
└── integration/
    └── test_diagnostic_trace.py     # NEW: stage coverage for success, failure, expiry, timeout

Dockerfile               # EDIT: create /var/log/openmedia owned by 10001
.gitignore .dockerignore # EDIT: logs/ and *.log
.env.example README.md   # EDIT: flag, directory, volume mount
CLAUDE.md                # EDIT: add specs/002-file-logging to "Where truth lives"
specs/001-media-download/contracts/{runtime,source-adapters}.md   # EDIT: four amendments
```

**Structure Decision**: Keep the flat `src/openmedia/` package and add one module. Logging
setup is cross-cutting, so it gets its own file instead of growing the 619-line
`__main__.py`. `SafeLogFormatter`'s redaction function moves into `diagnostics.py` and
`__main__.py` imports it, so there is one redaction implementation and no import cycle.

## Implementation order (input to /speckit-tasks)

1. **Setup**: ignore rules, `.env.example`, Dockerfile directory.
2. **Foundational**: settings and constants in `config.py`; `diagnostics.py` with handler,
   formatter, retention, queue wiring; flag-off wiring with `NullHandler`. Unit tests first.
3. **US1 (P1)**: `event()` call sites for every FR-002 stage, deadlines, error chains,
   worker output. Integration trace test.
4. **US2 (P2)**: day boundary, restart append, retention, lifecycle events, degraded mode.
5. **US3 (P3)**: `--check-config` directory probe, level setting, flag-off guarantees.
6. **Polish**: 001 contract amendments, README, `CLAUDE.md`, container check from
   quickstart §5.

## Risks

| Risk | Mitigation |
|---|---|
| A new event call site leaks a link to the console | Events with identifiers go only through `openmedia.diagnostic`, which has no console handler; test asserts captured stderr contains no `source_url` |
| Feature 001 tests or the timing audit depend on console text | Existing stage names and the console formatter are untouched; full suite runs in quickstart §1 |
| Wrong directory setting deletes operator files | Retention touches only names matching the strict pattern |
| Queue listener thread outlives shutdown and drops the last entries | `shutdown` event written, then `listener.stop()` flushes the queue inside the existing 20 s exit budget |
| Flag left on in production | Retention bounds disk use at 50 MB; personal data bounded at 14 days; documented in the contract |

## Complexity Tracking

No constitution violations. Nothing to justify.
