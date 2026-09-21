# Research: Diagnostic Log File

Inputs: [spec.md](spec.md), the constitution, feature 001's
[runtime contract](../001-media-download/contracts/runtime.md) and
[adapter contract](../001-media-download/contracts/source-adapters.md), and the current
logging code in `src/openmedia/__main__.py` (`SafeLogFormatter`, `configure_logging`,
`observe`) and `src/openmedia/workers.py` (`_read_stderr`).

No Technical Context item was left as NEEDS CLARIFICATION. Each section records one design
fork.

## 1. Logging library

- **Decision**: Python standard library `logging`. No new dependency.
- **Rationale**: The bot already logs through `logging` with a redacting formatter.
  Constitution IV asks to reuse what meets the requirement; the standard library does, and
  a second logging stack would leave two redaction paths to keep correct.
- **Alternatives considered**: `loguru` has built-in daily rotation and retention, but adds
  a dependency and bypasses `SafeLogFormatter`, so token redaction would be implemented
  twice. `structlog` improves structured fields only, and rotation would still be custom.

## 2. One file per day

- **Decision**: A small custom `logging.Handler` that derives the UTC date from each
  record's timestamp and appends to `openmedia-YYYY-MM-DD.log`. The clock is injectable for
  tests.
- **Rationale**: FR-019 needs the file *named for its day from the first byte*, and a
  restart must append. Choosing the file per record gives both with no rollover state.
- **Alternatives considered**: `TimedRotatingFileHandler(when="midnight", utc=True)` writes
  to a fixed base name and renames it at rollover, so today's file never carries today's
  date. Rollover time is computed from process start or file mtime, which misfires after a
  restart across midnight. Retention is by file count only, with no total-size limit.

## 3. Keeping the event loop unblocked (FR-011, SC-007)

- **Decision**: `QueueHandler` on the loggers, `QueueListener` thread owning the file
  handler. Queue bounded at 10,000 records; when full, the record is dropped and a drop
  counter is written as the next successful entry.
- **Rationale**: The bot is one asyncio loop. A direct file write on a stalled volume would
  freeze every request. With the queue, the loop pays for one `put_nowait`, and disk
  trouble stays on the listener thread. `queue.Queue` is in-process; it is not the "queue"
  service the constitution restricts.
- **Alternatives considered**: Direct synchronous writes are simpler and usually
  microseconds, but have no bound on a bad disk. `asyncio.to_thread` per record reorders
  entries and costs a thread hop each.

## 4. Entry format (FR-014)

- **Decision**: JSON Lines. One JSON object per line, UTF-8, keys in fixed order, tracebacks
  inside a string field so newlines are escaped.
- **Rationale**: Existing events are already `json.dumps` objects. One entry per line keeps
  `grep <request_id>` exact and makes `jq` filtering by stage or level possible. A
  multi-line traceback in plain text would break per-line filtering.
- **Alternatives considered**: Plain text lines read easier raw, but error chains span lines
  and detach from their request identifier. logfmt has weak tooling and awkward escaping for
  tracebacks.

## 5. Feature flag and where identifying data flows (FR-009, FR-018)

- **Decision**: `OPENMEDIA_DIAGNOSTIC_LOG` (`0` default, `1` on), read once at start. New
  stage events are emitted on a dedicated logger, `openmedia.diagnostic`, with
  `propagate=False`. The file handler is its only handler; with the flag off it has a
  `NullHandler`. Existing `openmedia` events keep going to the console and, with the flag
  on, also to the file.
- **Rationale**: This makes "identifying data never reaches the console" a property of the
  wiring instead of a rule every call site must remember. It also keeps console output
  byte-identical (FR-015), which protects feature 001's timing audit that parses it.
- **Alternatives considered**: One logger with a filter on the console handler works, but
  one misconfigured handler leaks links to `docker logs`. Checking the flag at each call
  site scatters the rule across the codebase.

## 6. Redaction in the file (FR-008, FR-009)

- **Decision**: The file formatter keeps token redaction everywhere and keeps URL redaction
  in free text (messages, error chains, worker output). The submitted link is written only
  through the structured `source_url` field, on the `received` entry, together with
  `chat_id` and `user_id`. Other entries carry `request_id` only.
- **Rationale**: Free-text URLs from source libraries are often signed media URLs with
  short-lived access signatures and the server's IP. The spec asks for the *submitted* link,
  which is what reproduces a failure. Writing identifiers once per trace keeps personal data
  to one line per request; `request_id` joins the rest.
- **Alternatives considered**: No URL redaction in the file is the most complete option, but
  stores signed URLs, which is outside FR-009. Identifiers on every entry make `grep chat_id`
  one step, at the cost of personal data on every line.

## 7. Worker diagnostic output (FR-006)

- **Decision**: Only the parent process writes log files. On worker failure the parent
  writes the already-sanitized `last_stderr` capture as the `worker_output` field.
- **Rationale**: One writer means no cross-process interleaving or locking. `_read_stderr`
  already bounds the capture and redacts URLs and tokens. The adapter contract's "never
  forwarded verbatim to routine logs" still holds for the console; the contract gains one
  sentence naming the flagged diagnostic file as the exception.
- **Alternatives considered**: Workers writing their own files means several writers per
  day file and the token-free worker environment would need the log path passed in.

## 8. Retention (FR-010)

- **Decision**: Fixed constants: 14 day files, 50,000,000 bytes total, 65,536 bytes per
  entry. Retention runs at start and when the first record of a new UTC day arrives. Only
  names matching `openmedia-\d{4}-\d{2}-\d{2}\.log` are touched. Age is judged by the date
  in the name, not mtime. Today's file is never removed; if it alone reaches the total
  limit, writing pauses until the next day and the console is told once.
- **Rationale**: A strict name pattern means a wrong directory setting cannot delete
  unrelated files. Name-based age survives file copies and restores that reset mtime.
- **Alternatives considered**: Configurable limits were rejected; the spec fixes them, like
  the project's deadlines. Compressing old days was rejected because 50 MB needs no
  compression and gzip breaks plain `grep`.

## 9. Write failures and crash safety (FR-011, edge cases)

- **Decision**: The handler overrides `handleError`: first failure prints one line to
  stderr and marks the log degraded; reopening is retried at most every 60 s; recovery
  prints one line. Each record is flushed after write, without `fsync`. On open, if the file
  does not end in a newline, a newline is written first.
- **Rationale**: Flush-per-record loses at most the last line on SIGKILL. The newline guard
  keeps one torn line from merging with the next entry. `fsync` per record would cost
  milliseconds each for a development aid.

## 10. Log location and deployment

- **Decision**: `OPENMEDIA_DIAGNOSTIC_LOG_DIR`, default `/var/log/openmedia`. It must be
  absolute and must not be inside `OPENMEDIA_WORK_DIR`. Directory mode `0700`, file mode
  `0600`. The image creates the default directory owned by UID 10001. Operators mount a
  named volume there when the flag is on. Local development uses
  `OPENMEDIA_DIAGNOSTIC_LOG_DIR=$PWD/logs`; `logs/` and `*.log` go in `.gitignore` and
  `.dockerignore`.
- **Rationale**: The work directory is tmpfs and is swept to empty at every start
  (`sweep_work_directories(..., older_than=0)`), so logs placed there would be deleted at
  exactly the moment they are needed. The image filesystem is read-only, so persistence
  needs a mount. A named volume inherits ownership from the image directory, which avoids a
  host `chown` step.
- **Alternatives considered**: A bind mount works but the host directory must be owned by
  10001 first; documented as the alternative.

## 11. Detail level (FR-012)

- **Decision**: `OPENMEDIA_DIAGNOSTIC_LOG_LEVEL`, default `DEBUG`, same allowed values as
  `OPENMEDIA_LOG_LEVEL`. `INFO` records stage events; `DEBUG` adds worker protocol messages
  and coalesced progress. Transport loggers (`httpx`, `httpcore`, `telegram`, `urllib3`,
  `requests`) stay capped at `WARNING`.
- **Rationale**: A separate setting lets the console stay at `INFO` while the file is
  complete. Transport debug logs contain the bot token inside request URLs; the runtime
  contract already disables them and redaction should be the second line of defence, not
  the first.

## 12. Command-line modes

- **Decision**: `--healthcheck` and `--check-config` never open a log file or start the
  listener. With the flag on, `--check-config` validates the directory by creating it and
  writing then deleting a probe file. With the flag off, the directory setting is ignored.
- **Rationale**: The healthcheck runs every 30 s and would otherwise create files and write
  noise. FR-013 limits validation to the flag-on case; SC-008 requires zero files with the
  flag off.
