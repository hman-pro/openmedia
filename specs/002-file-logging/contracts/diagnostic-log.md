# Diagnostic Log Contract

The operator-facing surface of feature 002: environment variables, files on disk, the line
format, and amendments to feature 001's contracts. Field details are in
[data-model.md](../data-model.md).

## Configuration

| Variable | Default | Validation/meaning |
|---|---|---|
| OPENMEDIA_DIAGNOSTIC_LOG | `0` | Feature flag. `1` turns the diagnostic log on; only `0` and `1` are accepted. Read at start |
| OPENMEDIA_DIAGNOSTIC_LOG_DIR | `/var/log/openmedia` | Used only when the flag is on. Absolute; not inside `OPENMEDIA_WORK_DIR`; must be creatable and writable |
| OPENMEDIA_DIAGNOSTIC_LOG_LEVEL | `DEBUG` | Used only when the flag is on. `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG` |

Fixed values, changed only by a spec update: 14 day files, 50,000,000 bytes total, 65,536
bytes per entry.

## Guarantees

**Flag off** (default):

- No file or directory is created, including by `--check-config`.
- `OPENMEDIA_DIAGNOSTIC_LOG_DIR` and `OPENMEDIA_DIAGNOSTIC_LOG_LEVEL` are not validated.
- Console output matches feature 001, plus one plain `openmedia: started (diagnostic_log=off)`
  line at start and one `openmedia: stopped (reason=…)` line at exit.
- Submitted links and Telegram identifiers are written nowhere.

**Flag on**:

- Entries go to `<dir>/openmedia-YYYY-MM-DD.log`, UTC date, append-only, mode `0600` inside a
  `0700` directory.
- Console output still matches feature 001 plus the same start and stop lines, which name the
  log directory. Links stay redacted there.
- The file holds submitted links and Telegram chat and user identifiers on `received`
  entries. It holds no token, no signed media URL, no media bytes, no names or usernames.
- (amended by 004) Links and Telegram identifiers also appear on `refused` entries, and a
  query-free `resolved_url` may appear on `inspection_finished` for a LinkedIn short link.
  The exclusions above still hold. See
  [telegram-bot.md (004)](../../004-linkedin-share-links/contracts/telegram-bot.md#refused-messages-in-the-diagnostic-log).
- A log write problem never changes a request's outcome. The console gets one line when
  writing stops and one when it resumes.
- Only files matching `openmedia-\d{4}-\d{2}-\d{2}\.log` in the directory are ever deleted.

## Command-line modes

| Command | Flag on behavior |
|---|---|
| `python -m openmedia --check-config` | Validates the directory with a probe file, then removes the probe. Exit 2 with `OPENMEDIA_DIAGNOSTIC_LOG_DIR ... : <reason>` on failure. Writes no entries |
| `python -m openmedia --healthcheck` | Never opens or writes the log |
| `python -m openmedia` | Runs retention, writes `startup`, then logs until `shutdown` or `crash` |

## Line format

One JSON object per line, UTF-8, `\n` terminated. Example trace, shortened:

```json
{"ts":"2026-09-21T14:03:11.204Z","level":"INFO","origin":"request","stage":"received","request_id":"9f2c…","platform":"youtube","elapsed_seconds":0.0003,"source_url":"https://www.youtube.com/watch?v=…","chat_id":123456789,"user_id":123456789}
{"ts":"2026-09-21T14:03:11.209Z","level":"INFO","origin":"request","stage":"inspection_started","request_id":"9f2c…","platform":"youtube","elapsed_seconds":0.0051}
{"ts":"2026-09-21T14:04:11.210Z","level":"ERROR","origin":"request","stage":"inspection_finished","request_id":"9f2c…","platform":"youtube","elapsed_seconds":60.0012,"outcome":"failed","error_category":"timeout","failed_stage":"inspection","deadline":"inspection","deadline_seconds":60,"worker_output":"ERROR: <redacted-url> …"}
```

## Deployment

The image creates `/var/log/openmedia` owned by UID/GID 10001. With the flag on, mount
persistent storage there; the image filesystem stays read-only:

```sh
docker run … --read-only \
  -e OPENMEDIA_DIAGNOSTIC_LOG=1 \
  -v openmedia-logs:/var/log/openmedia \
  …
```

A bind mount also works when the host directory is owned by 10001. With the flag on and no
mount, startup fails the writability check instead of logging to nowhere.

## Amendments to feature 001 contracts

Applied to the 001 files during implementation, each marked "(amended by 002)":

1. `contracts/runtime.md`, Configuration table: add the three variables above.
2. `contracts/runtime.md`, Deployment shape: "No … persistent media volume" stays true; add
   that an optional log volume is mounted when the diagnostic flag is on.
3. `contracts/runtime.md`, Build and notices: "Log rotation is configured by the container
   runtime" applies to console output; the diagnostic files manage their own retention.
   `.dockerignore` also excludes `logs/` and `*.log`.
4. `contracts/source-adapters.md`, line 6: sanitized worker stderr is still never forwarded
   to users or the console; the flagged diagnostic file is the one permitted destination.
